"""Standards knowledge base loading and lookup.

Resolving a material grade to its acceptance limits is **deterministic**. Given
the same certificate twice, the same thresholds come back, and an unrecognised
grade returns nothing rather than the nearest thing found.

This is a design decision, not an implementation shortcut. Fuzzy retrieval on
this path has a silent failure mode: return Grade 60 limits for a Grade 70
certificate and the downstream arithmetic runs perfectly, producing a confident
wrong PASS. With a few dozen grades, an alias table plus a spec/grade parser is
both more accurate and fully auditable.

Lookup proceeds in two passes:

1. Exact match of the normalised grade string against the alias table.
2. Structural match -- pull the specification number and grade token out of the
   string ("ASME SA-516 Gr.70" -> spec 516, grade 70) and match on those.

If neither hits, the caller gets `StandardNotFoundError`.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

from models.standards import Requirement, ResolvedThresholds, StandardEntry

logger = logging.getLogger(__name__)

DEFAULT_DATA_PATH = Path(__file__).parent / "standards_data" / "astm_asme.json"

# "A516", "SA-516", "sa 516", "ASTM A106" -> the specification number.
# A trailing digit-lookahead rather than \b, so the unspaced "A516GR70" form
# that appears on real certificates still resolves.
_SPEC_PATTERN = re.compile(r"\bs?a[\s\-]?(\d{2,4})m?(?!\d)")

# "TP304", "TYPE 316L" -> a stainless type designation.
_TYPE_PATTERN = re.compile(r"\b(?:tp|type)[\s\-]?(\d{3}[a-z]?)\b")

# "Gr.70", "GRADE B", "Gr B7" -> an explicit grade token.
_GRADE_PATTERN = re.compile(r"\bgr(?:ade)?[\s\.\-]*([a-z]?\d{1,3}[a-z]?)\b")

# A bare grade token such as the "B7" in "A193 B7".
_BARE_GRADE_PATTERN = re.compile(r"\b([a-z]\d{0,2})\b")


class StandardNotFoundError(LookupError):
    """No knowledge base entry matches the material grade.

    Deliberately an error rather than a null result: the caller must surface
    "standard not found" to the inspector, never treat it as "nothing to check".
    """


class ThicknessRequiredError(LookupError):
    """The grade's limits vary by thickness, but the certificate has no thickness.

    Picking a band arbitrarily would silently apply the wrong limits, so the
    caller routes the document to human review instead.
    """


class ThicknessOutOfRangeError(LookupError):
    """The certificate's thickness falls outside every band defined for the grade."""


def _clean(text: str) -> str:
    """Lowercase and reduce punctuation to single spaces."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _squash(text: str) -> str:
    """Reduce a string to alphanumerics only, for exact alias comparison."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def structural_key(text: str | None) -> str | None:
    """Reduce a grade string to a canonical "spec|grade" key.

    Examples:
        "ASTM A516 Grade 70"  -> "516|70"
        "SA-516 Gr.70"        -> "516|70"
        "ASME SA-240 TP304"   -> "240|tp304"
        "A240 Type 304"       -> "240|tp304"
        "A193 B7"             -> "193|b7"
        "ASTM A36"            -> "36|-"

    Returns None when no specification number can be found, since a grade token
    on its own ("70") is ambiguous across specifications.
    """
    if not text:
        return None

    cleaned = _clean(text)

    spec_match = _SPEC_PATTERN.search(cleaned)
    if not spec_match:
        return None
    spec = spec_match.group(1)

    # Remove the specification itself so its digits cannot be read as a grade.
    remainder = cleaned[: spec_match.start()] + " " + cleaned[spec_match.end() :]
    remainder = re.sub(r"\b(?:astm|asme|sa|a)\b", " ", remainder)
    # Drop edition years such as "-17" or "2017" that follow a specification.
    remainder = re.sub(r"\b(?:19|20)\d{2}\b", " ", remainder)
    remainder = re.sub(r"\bm\b", " ", remainder).strip()

    type_match = _TYPE_PATTERN.search(remainder)
    if type_match:
        return f"{spec}|tp{type_match.group(1)}"

    grade_match = _GRADE_PATTERN.search(remainder)
    if grade_match:
        return f"{spec}|{grade_match.group(1)}"

    # A standalone number is a grade only when it is not the specification.
    number_match = re.search(r"\b(\d{2,3})\b", remainder)
    if number_match and number_match.group(1) != spec:
        return f"{spec}|{number_match.group(1)}"

    bare_match = _BARE_GRADE_PATTERN.search(remainder)
    if bare_match:
        return f"{spec}|{bare_match.group(1)}"

    return f"{spec}|-"


class StandardsKnowledgeBase:
    """In-memory index over the curated standards table."""

    def __init__(self, entries: list[StandardEntry]) -> None:
        self.entries = entries
        self._by_key: dict[str, StandardEntry] = {}
        self._by_alias: dict[str, StandardEntry] = {}
        self._by_structural: dict[str, StandardEntry] = {}

        for entry in entries:
            self._by_key[entry.canonical_key] = entry

            for alias in [*entry.aliases, f"{entry.specification} {entry.grade}"]:
                self._by_alias[_squash(alias)] = entry

            derived = structural_key(f"{entry.specification} {entry.grade}")
            if derived:
                if derived in self._by_structural:
                    logger.warning(
                        "Duplicate structural key %s: %s collides with %s",
                        derived,
                        entry.canonical_key,
                        self._by_structural[derived].canonical_key,
                    )
                self._by_structural[derived] = entry

    def __len__(self) -> int:
        return len(self.entries)

    @property
    def unverified_keys(self) -> list[str]:
        """Entries not yet checked by a qualified reviewer."""
        return [e.canonical_key for e in self.entries if not e.verified]

    def find_entry(self, grade_identifier: str | None) -> StandardEntry:
        """Resolve a grade string to a knowledge base entry.

        Raises:
            StandardNotFoundError: No entry matches.
        """
        if not grade_identifier or not grade_identifier.strip():
            raise StandardNotFoundError("No material grade was extracted")

        squashed = _squash(grade_identifier)
        if squashed in self._by_alias:
            return self._by_alias[squashed]

        derived = structural_key(grade_identifier)
        if derived and derived in self._by_structural:
            return self._by_structural[derived]

        raise StandardNotFoundError(
            f"No knowledge base entry for material grade {grade_identifier!r}"
        )

    def lookup(
        self,
        grade_identifier: str | None,
        product_form: str | None = None,
        thickness_mm: float | None = None,
    ) -> ResolvedThresholds:
        """Resolve a certificate to the single requirement block that governs it.

        Raises:
            StandardNotFoundError: The grade is not in the knowledge base.
            ThicknessRequiredError: Limits are thickness-dependent and no
                thickness was extracted.
            ThicknessOutOfRangeError: The thickness matches no defined band.
        """
        entry = self.find_entry(grade_identifier)
        notes: list[str] = []

        candidates = [r for r in entry.requirements if r.covers_form(product_form)]
        if not candidates:
            candidates = entry.requirements
            if product_form:
                notes.append(
                    f"Product form '{product_form}' does not match any requirement "
                    f"block for {entry.canonical_key}; general requirements applied."
                )

        if not candidates:
            raise StandardNotFoundError(
                f"Entry {entry.canonical_key} defines no requirements"
            )

        requirement, matched_on_thickness = self._select_requirement(
            entry, candidates, thickness_mm
        )

        if not entry.verified:
            notes.append(
                f"Threshold values for {entry.canonical_key} are UNVERIFIED. "
                "They have not been checked against the governing code edition."
            )

        return ResolvedThresholds(
            canonical_key=entry.canonical_key,
            specification=entry.specification,
            grade=entry.grade,
            clause_reference=entry.clause_reference,
            verified=entry.verified,
            requirement=requirement,
            matched_on_thickness=matched_on_thickness,
            notes=notes,
        )

    @staticmethod
    def _select_requirement(
        entry: StandardEntry,
        candidates: list[Requirement],
        thickness_mm: float | None,
    ) -> tuple[Requirement, bool]:
        """Pick the requirement block matching the certificate's thickness."""
        unbounded = [
            r
            for r in candidates
            if r.thickness_min_mm is None and r.thickness_max_mm is None
        ]

        if thickness_mm is None:
            if unbounded:
                return unbounded[0], False
            if len(candidates) == 1:
                return candidates[0], False
            raise ThicknessRequiredError(
                f"{entry.canonical_key} defines {len(candidates)} thickness-dependent "
                "requirement bands, but no thickness was extracted from the "
                "certificate. The applicable limits cannot be determined."
            )

        matching = [r for r in candidates if r.covers_thickness(thickness_mm)]
        if matching:
            selected = matching[0]
            bounded = (
                selected.thickness_min_mm is not None
                or selected.thickness_max_mm is not None
            )
            return selected, bounded

        if unbounded:
            return unbounded[0], False

        raise ThicknessOutOfRangeError(
            f"Thickness {thickness_mm} mm falls outside every band defined for "
            f"{entry.canonical_key}"
        )


def load_standards(path: Path | None = None) -> StandardsKnowledgeBase:
    """Load and validate the standards table from disk.

    Raises:
        FileNotFoundError: The data file is missing.
        ValueError: The file is malformed or contains duplicate canonical keys.
    """
    data_path = path or DEFAULT_DATA_PATH

    if not data_path.exists():
        raise FileNotFoundError(f"Standards data file not found: {data_path}")

    with data_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    raw_entries = payload.get("standards")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise ValueError(f"No 'standards' array found in {data_path}")

    entries = [StandardEntry.model_validate(item) for item in raw_entries]

    keys = [e.canonical_key for e in entries]
    duplicates = {k for k in keys if keys.count(k) > 1}
    if duplicates:
        raise ValueError(f"Duplicate canonical_key values in {data_path}: {duplicates}")

    kb = StandardsKnowledgeBase(entries)
    logger.info(
        "Loaded %s standards (%s unverified)", len(kb), len(kb.unverified_keys)
    )
    return kb


@lru_cache(maxsize=1)
def get_knowledge_base() -> StandardsKnowledgeBase:
    """Return the process-wide knowledge base, loaded once."""
    return load_standards()
