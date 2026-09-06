"""Form template loading and format-number lookup.

Resolving a scanned page to its template is **deterministic**. The same page
twice gives the same template, and an unrecognised format number returns
`template_unknown` rather than the nearest thing on file.

## Why canonicalisation, and why it is not fuzzy matching

Five of the six sample documents are scans carrying an OCR'd text layer, and
that layer mangles the format number every time:

    printed                    OCR text layer
    NPCIL/QMD/TF-127, Rev.R0   NPCILQMDITF- 127, Rev.RO
    NPCIL/QMD/TF-127, Rev.R0   NPCIUOMD/TF- 127, Rev.RO
    NPCIL/QMD/TF053-R1         NPCILIOMDI TFO53 -R1
    FQ/069 Rev.2               FQ/ D69 Rev.2
    NPCIL/QMD/TF/216           NPCIL/QMD/TF/216      (born-digital, clean)

Note what survives and what does not. The `NPCIL/QMD/` prefix is destroyed
differently every time -- `/` reads as `I`, `U` or nothing; `Q` reads as `O` --
so it is near-useless as a discriminator. What survives is the family token and
the number: `TF` `127`, `FQ` `069`. Those are what we key on.

So the lookup runs a fixed, documented character-confusion map (`O`->`0`,
`D`->`0`, `I`->`1`) over the *numeric* field only, resolves the family token
through an explicit alias table, and then does an **exact** dictionary lookup.

That is canonicalisation, not fuzzy matching, and the distinction is the whole
point. Every substitution is a listed rule a reviewer can audit; there is no
similarity score and no nearest match. Anything that does not canonicalise to a
key in the registry fails loudly -- the same discipline
`knowledge_base/standards_loader.py` applies to material grades, and for the
same reason: on this path a confident wrong answer has no visible symptom.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

from models.template import FormTemplate

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATE_DIR = Path(__file__).parent / "templates"

# Bumped when the canonicalisation rules below change. Stamped onto stored
# classifications so a historical verdict stays reproducible: a format number
# that resolved under v1 rules must still be explainable after v2 ships.
REGISTRY_VERSION = "1"

# Digit-position confusions seen in the sample OCR text layers. Applied *only*
# where a digit is expected, never to a whole string -- mapping letters to
# digits globally would turn "SMAW" into "5MAW".
#
# Every entry is a reading actually observed or a direct visual twin of one:
#   O -> 0   "TFO53" for TF053, "Rev.RO" for Rev.R0
#   D -> 0   "FQ/ D69" for FQ/069
#   I,L -> 1 stroke-for-stroke twins in this scanner's output
#   S -> 5, B -> 8, Z -> 2, G -> 6, Q -> 0
_DIGIT_CONFUSIONS = str.maketrans(
    {
        "O": "0", "D": "0", "Q": "0",
        "I": "1", "L": "1",
        "Z": "2",
        "S": "5",
        "G": "6",
        "B": "8",
    }
)

# Family token aliases. Deliberately minimal: every entry is a reading
# actually observed in the sample packages, not a plausible-looking twin.
#
# `TE` is the one misread on file -- "NPCIL/OMD/TE. 114(R0)" for TF-114, where
# the crossbar of the F drops out. Speculative aliases were tried and removed:
# adding `FO` as an `FQ` twin made "TFO53" resolve to FQ-053 instead of
# TF-053, because the alias table widened the false-match surface faster than
# it widened coverage. An unrecognised family must return `template_unknown`
# and get a real alias added once a real scan justifies it -- never a guess.
_FAMILY_ALIASES = {
    "TF": "TF",
    "TE": "TF",
    "FQ": "FQ",
}

# The issuer prefix, however mangled. OCR routinely welds it to the family
# token -- "NPCILQMDITF- 127" has no word boundary before the TF -- so the
# prefix has to be consumed explicitly rather than relied on as a delimiter.
#
# Covers every reading observed: NPCIL/QMD/, NPCILQMDI, NPCILUQMDI, NPCIUOMD/,
# NPCILIOMDI, NPCIL/OMD/, and NPCIQMDI (what NPCIƯQMDI becomes once the
# non-ASCII character is stripped). The `[QO0]` class is the Q->O confusion.
# The trailing class holds only characters that are themselves renderings of
# the "/" separator (`I`, `L`, `U`) or real punctuation. It must NOT admit
# arbitrary letters: an `[A-Z]` class here greedily swallows the `T` of a
# following `TF`, leaving `FO` to match as a family token.
_ISSUER_PREFIX = r"NPCI[A-Z0-9/]{0,3}[QO0]MD[ILU/.\s]{0,3}"

# A family token, optional separator noise, then a 2-4 character number field
# whose characters may be digits or their listed letter twins.
#
# The family token is reached either through the issuer prefix above or at a
# plain word boundary (the WPQR prints a bare "FQ/069", the requisition sheet a
# clean "NPCIL/QMD/TF/216"). Anchoring it this way is what stops "TF" inside an
# unrelated word being read as a format number.
#
# The separator class covers every joiner seen: "/", "-", ".", " ", the empty
# string ("TFO53"), and the letters `I`, `L`, `U` -- which are how this scanner
# renders a "/". The WPQR's second page reads "FQI069" for "FQ/069".
#
# That creates a real ambiguity, because `I` is *also* a rendering of the digit
# 1. It is resolved by position rather than by preference: the separator run is
# greedy, so a leading `I` is consumed as the "/" it almost always is, and the
# number's FIRST character is restricted to digits and their non-separator
# twins (`[0-9ODQZSGB]`) so it cannot start with one. Without that restriction
# "FQI069" canonicalises to FQ-1069-R2 and silently misses its own template.
#
# The cost is that a form number whose leading 1 is misread as `I` ("TFI27")
# resolves to the wrong key and reports template_unknown. That is the correct
# trade: it fails loudly rather than matching the wrong form.
#
# The pattern deliberately does not allow arbitrary words between the token and
# its number. The Weld Data Record's text layer separates them by several lines
# ("NPCIL/OMD/TE." ... "114(R0)"), so that page reports template_unknown rather
# than being stitched back together by a heuristic. Reassembling it needs the
# word geometry and belongs with TF-114's template, which is not yet built.
_FORMAT_PATTERN = re.compile(
    rf"(?:\b{_ISSUER_PREFIX}|\b)"
    r"(?P<family>TF|TE|FQ)"
    r"(?P<sep>[\s\-/.,:()#ILU]{0,4})"
    r"(?P<number>[0-9ODQZSGB][0-9ODQILZSGB]{1,3})(?![0-9ODQILZSGB])"
)

# Revision, in any of the printed forms: "Rev.R0", "Rev.RO", "-R1", "(R0)",
# "Rev.2", "R0". A bare number after "Rev" is normalised to "R<n>", so the
# WPQR's "Rev.2" and a hypothetical "Rev.R2" land on the same key.
_REVISION_PATTERN = re.compile(
    r"(?:REV\.?\s*R?|[\-(]\s*R)\s*(?P<rev>[0-9ODQILZSGB])\b",
    re.IGNORECASE,
)


class TemplateNotFoundError(LookupError):
    """No template matches the canonical key.

    Deliberately an error rather than a null result: the caller must surface
    `template_unknown` and fall back to whole-page extraction, never treat a
    miss as "nothing to read".
    """


def _strip_to_ascii(text: str) -> str:
    """Drop non-ASCII characters an OCR layer invents.

    The sample identity card contains `NPCIƯQMDITF- 127` -- U+01AF, a letter
    that appears on no NPCIL form. Removing it rather than transliterating is
    correct: it sits in the prefix we do not key on.
    """
    return "".join(ch for ch in text if ord(ch) < 128)


def _normalise_number(raw: str) -> str:
    """Reduce an OCR'd number field to digits, zero-padded to three.

    Padding makes "FQ/069" and a hypothetical "FQ/69" the same key, which is
    right: the leading zero is a typesetting choice, not an identity.

    Returns "" when the field does not fully resolve to digits, so the caller
    can reject it rather than key on a partial read.
    """
    converted = raw.upper().translate(_DIGIT_CONFUSIONS)
    if not converted.isdigit():
        return ""
    return converted.zfill(3)


def _normalise_revision(raw: str) -> str:
    """Reduce a revision token to "R<digit>", or "" when it does not resolve."""
    converted = raw.upper().translate(_DIGIT_CONFUSIONS)
    if not converted.isdigit():
        return ""
    return f"R{converted}"


def canonical_key(text: str | None) -> str | None:
    """Reduce printed format-number text to a registry key.

    Examples:
        "Format No. NPCILQMDITF- 127, Rev.RO"  -> "TF-127-R0"
        "Format No. NPCIUOMD/TF- 127, Rev.RO"  -> "TF-127-R0"
        "Form No. FQ/ D69 Rev.2"               -> "FQ-069-R2"
        "Format No NPCILIOMDI TFO53 -R1"       -> "TF-053-R1"
        "Format No: NPCIL/QMD/TF/216"          -> "TF-216"

    Returns None when no family token and number can be found at all -- a bare
    number is ambiguous across forms and must never key on its own.

    The revision is appended only when one is printed. `NPCIL/QMD/TF/216`
    carries no revision, so its key is "TF-216"; adding a guessed "-R0" would
    invent a distinction the form does not make.
    """
    if not text:
        return None

    cleaned = re.sub(r"\s+", " ", _strip_to_ascii(text).upper())

    match = _FORMAT_PATTERN.search(cleaned)
    if not match:
        return None

    family = _FAMILY_ALIASES.get(match.group("family"))
    if not family:  # pragma: no cover - pattern and table are kept in step
        return None

    number = _normalise_number(match.group("number"))
    if not number:
        return None

    # Look for the revision only *after* the number, so a stray "R" earlier in
    # the prefix ("...QMD/R...") cannot be read as one.
    tail = cleaned[match.end() :]
    revision_match = _REVISION_PATTERN.search(tail)
    if revision_match:
        revision = _normalise_revision(revision_match.group("rev"))
        if revision:
            return f"{family}-{number}-{revision}"

    return f"{family}-{number}"


def canonical_keys(text: str | None) -> list[str]:
    """Every distinct key found in `text`, in order of appearance.

    A page can legitimately print its format number more than once -- the
    welder identity card carries it on both the front and the back face. Those
    resolve to the same key and collapse here. Two *different* keys on one page
    means the classifier cannot tell what the page is, and the caller reports
    AMBIGUOUS rather than picking one.
    """
    if not text:
        return []

    cleaned = re.sub(r"\s+", " ", _strip_to_ascii(text).upper())
    found: list[str] = []

    for match in _FORMAT_PATTERN.finditer(cleaned):
        # Re-run the full single-key path over this match plus its tail, so
        # revision handling stays in exactly one place.
        key = canonical_key(cleaned[match.start() : match.end() + 24])
        if key and key not in found:
            found.append(key)

    return found


def _load_templates(directory: Path) -> dict[str, FormTemplate]:
    """Load and validate every template JSON in `directory`."""
    templates: dict[str, FormTemplate] = {}

    if not directory.is_dir():
        raise TemplateNotFoundError(f"Template directory not found: {directory}")

    for path in sorted(directory.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TemplateNotFoundError(f"Could not read template {path}: {exc}") from exc

        template = FormTemplate.model_validate(raw)

        # The key is derived from the declared format number rather than taken
        # on trust, so a template whose canonical_key disagrees with its own
        # printed format number is rejected at load rather than silently
        # shadowing another form.
        derived = canonical_key(f"{template.format_no} Rev.{template.format_rev}")
        if derived != template.canonical_key:
            raise TemplateNotFoundError(
                f"{path.name}: canonical_key '{template.canonical_key}' does not "
                f"match format number '{template.format_no} "
                f"Rev.{template.format_rev}' which canonicalises to '{derived}'"
            )

        if template.canonical_key in templates:
            raise TemplateNotFoundError(
                f"{path.name}: duplicate canonical_key '{template.canonical_key}'"
            )

        templates[template.canonical_key] = template

    if not templates:
        raise TemplateNotFoundError(f"No templates found in {directory}")

    return templates


@lru_cache(maxsize=4)
def load_registry(directory: str | None = None) -> dict[str, FormTemplate]:
    """Return the template registry, keyed by canonical key.

    Cached: templates are read-only reference data and the JSON does not change
    while the process runs.
    """
    path = Path(directory) if directory else DEFAULT_TEMPLATE_DIR
    registry = _load_templates(path)

    unverified = [k for k, t in registry.items() if not t.verified]
    if unverified:
        logger.warning(
            "Template registry loaded with %d unverified template(s): %s. "
            "Values read through these must be flagged in any output.",
            len(unverified),
            ", ".join(sorted(unverified)),
        )

    return registry


def get_template(key: str, directory: str | None = None) -> FormTemplate:
    """Look up one template by canonical key.

    Raises:
        TemplateNotFoundError: The key is not in the registry.
    """
    registry = load_registry(directory)
    try:
        return registry[key]
    except KeyError:
        raise TemplateNotFoundError(
            f"No template registered for '{key}'. Known keys: "
            f"{', '.join(sorted(registry))}"
        ) from None


def known_keys(directory: str | None = None) -> list[str]:
    """Every canonical key the registry can resolve, sorted."""
    return sorted(load_registry(directory))
