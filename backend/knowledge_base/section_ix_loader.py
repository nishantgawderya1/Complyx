"""Section IX rule table loading and lookup.

The same discipline as `standards_loader.py`, for the same reason: this is a
**table lookup, not a search**. QW-461.9, QW-452.1 and QW-433 map discrete
inputs to discrete outputs, and a lookup that returns the nearest row instead of
the right one produces a confident wrong qualified range -- which looks exactly
like a right one on paper and surfaces only when a welder works outside their
actual qualification.

So: explicit alias tables, exact matching, and `RuleNotFoundError` on a miss.
There is no fuzzy path and no default row.

Every lookup returns its `Provenance` alongside the answer, carrying the clause,
the page of the code it was read from, and whether a reviewer has signed that
specific row. Callers must surface the unsigned state; `DerivationResult.issuable`
refuses to go true while any row is unsigned.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from models.derivation import (
    Backing,
    CouponForm,
    Progression,
    Provenance,
    TestRequirement,
)

logger = logging.getLogger(__name__)

DEFAULT_RULES_PATH = Path(__file__).parent / "section_ix_data" / "qw_rules.json"

# Position letters, in the order the code prints them.
POSITION_ORDER = ["F", "H", "V", "O", "SP"]
ALL_POSITIONS = ["F", "H", "V", "O"]


class RuleNotFoundError(LookupError):
    """No encoded rule row covers this input.

    Deliberately an error rather than a null result. The caller must surface
    "rule not found" and route to REVIEW -- never treat it as "no restriction",
    which is how a missing rule becomes an unlimited qualification.
    """


class RuleNotEncodedError(RuleNotFoundError):
    """The rule exists in the code but has not been transcribed yet.

    Separated from RuleNotFoundError so the UI can say "we have not encoded
    QW-423 yet" rather than "your input is unrecognised" -- a different message
    to a different person, and only one of them is the inspector's problem.
    """


def _squash(text: str) -> str:
    """Reduce to lowercase alphanumerics for exact alias comparison."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


@lru_cache(maxsize=4)
def load_rules(path: str | None = None) -> dict[str, Any]:
    """Load the QW rule tables. Cached: read-only reference data."""
    target = Path(path) if path else DEFAULT_RULES_PATH
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuleNotFoundError(f"Could not read rule tables at {target}: {exc}") from exc

    unsigned = _count_unsigned(data)
    if unsigned:
        logger.warning(
            "Section IX rule tables loaded with %d unsigned row(s) (%s). These "
            "must be visibly flagged and must not back a record issued to the "
            "field until a reviewer signs them.",
            unsigned,
            data.get("kb_version"),
        )
    return data


def _count_unsigned(data: dict[str, Any]) -> int:
    """Count rule rows with no reviewer signature, at any depth."""
    total = 0

    def walk(node: Any) -> None:
        nonlocal total
        if isinstance(node, dict):
            if "verified" in node and node.get("verified") is False:
                total += 1
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return total


def _provenance(data: dict[str, Any], table: dict[str, Any], row: dict[str, Any] | None) -> Provenance:
    """Build provenance from a table and the specific row that matched."""
    source = row if row and "verified" in row else table
    return Provenance(
        clause_ref=table.get("clause_ref", "?"),
        source_page=table.get("source_page"),
        code_edition=data.get("code_edition", "unknown"),
        kb_version=data.get("kb_version", "unknown"),
        verified=bool(source.get("verified", False)),
        verified_by=source.get("verified_by"),
        verified_date=source.get("verified_date"),
    )


def _format_positions(positions: list[str]) -> str:
    """Render a position list the way the code prints it."""
    if positions == ["ALL"]:
        return "All positions"
    ordered = [p for p in POSITION_ORDER if p in positions]
    return ", ".join(ordered)


def qualified_positions(
    coupon_form: CouponForm,
    test_position: str,
    path: str | None = None,
) -> tuple[str, Provenance]:
    """Table QW-461.9 — what positions a coupon qualifies.

    Returns the qualified range as the code states it, spanning the groove
    columns and the fillet/tack column, plus provenance.

    Raises:
        RuleNotFoundError: No row for this coupon form and test position.
    """
    data = load_rules(path)
    table = data["qw_461_9"]

    wanted = test_position.strip().upper().replace(" ", "")
    for row in table["rows"]:
        if row["coupon"] != coupon_form.value:
            continue
        if row["test_position"].upper().replace(" ", "") != wanted:
            continue

        parts: list[str] = []
        over = row.get("groove_plate_and_pipe_over_610")
        under = row.get("groove_pipe_610_and_under")
        fillet = row.get("fillet_or_tack")

        if over:
            parts.append(
                f"Groove, plate and pipe over 610 mm O.D.: {_format_positions(over)}"
            )
        if under:
            suffix = " (73 mm O.D. and over)" if row.get("pipe_note_3") else ""
            parts.append(
                f"Groove, pipe 610 mm O.D. and under{suffix}: {_format_positions(under)}"
            )
        if fillet:
            parts.append(f"Fillet or tack: {_format_positions(fillet)}")

        return "; ".join(parts), _provenance(data, table, row)

    raise RuleNotFoundError(
        f"Table QW-461.9 has no row for {coupon_form.value} in position "
        f"'{test_position}'. Encoded positions for this coupon form: "
        + ", ".join(
            r["test_position"] for r in table["rows"] if r["coupon"] == coupon_form.value
        )
    )


def required_tests(thickness_mm: float, path: str | None = None) -> TestRequirement:
    """Table QW-452.1(a) — tests required for a coupon of this thickness.

    Raises:
        RuleNotFoundError: The thickness falls outside every encoded band.
    """
    data = load_rules(path)
    table = data["qw_452_1a"]

    for band in table["bands"]:
        low = band["min_mm"]
        high = band["max_mm"]
        if thickness_mm < low:
            continue
        if high is not None and thickness_mm >= high:
            continue
        return TestRequirement(
            visual=band["visual"],
            side_bend=band["side_bend"],
            face_bend=band["face_bend"],
            root_bend=band["root_bend"],
            substitution_note=band.get("substitution_note"),
            provenance=_provenance(data, table, band),
        )

    raise RuleNotFoundError(
        f"Table QW-452.1(a) has no band covering {thickness_mm} mm."
    )


def qualified_thickness(
    thickness_mm: float,
    layers: int | None,
    path: str | None = None,
) -> tuple[str, Provenance]:
    """Table QW-452.1(b) — thickness of weld metal qualified.

    The three-layer rule needs BOTH a coupon of 13 mm or more AND three or more
    layers. `layers` of None is not treated as "fewer than three": an unknown
    layer count on a coupon thick enough to matter raises, because the answer
    genuinely differs and guessing it is the single most consequential wrong
    call on the form.

    Raises:
        RuleNotFoundError: The layer count is unknown and would change the answer.
    """
    data = load_rules(path)
    table = data["qw_452_1b"]

    three_layer_rule = next(r for r in table["rules"] if r["id"] == "max_to_be_welded")
    twice_t = next(r for r in table["rules"] if r["id"] == "twice_t")

    thick_enough = thickness_mm >= three_layer_rule["min_thickness_mm"]

    if thick_enough and layers is None:
        raise RuleNotFoundError(
            f"QW-452.1(b): a {thickness_mm} mm coupon qualifies 'maximum to be "
            "welded' with three or more layers and only 2t without, and the "
            "layer count is unknown. The answer differs, so it is not derived."
        )

    if thick_enough and layers is not None and layers >= 3:
        return three_layer_rule["qualified"], _provenance(data, table, three_layer_rule)

    return f"2t = {thickness_mm * 2:g} mm", _provenance(data, table, twice_t)


def f_number_for_electrode(classification: str, path: str | None = None) -> tuple[int, Provenance]:
    """Resolve an electrode classification to its F-number.

    Exact alias match only. `E7018`, `E-7018` and `SFA 5.1 E7018` all resolve
    through the listed aliases; anything else raises rather than resolving to
    the nearest-looking entry.
    """
    data = load_rules(path)
    table = data["qw_433"]
    squashed = _squash(classification)

    for entry in table["electrode_f_numbers"]:
        if squashed in {_squash(a) for a in entry["aliases"]}:
            return entry["f_number"], _provenance(data, table, entry)

    # A bare classification embedded in a longer string, e.g. "SFA5.1 E7018".
    for entry in table["electrode_f_numbers"]:
        for alias in entry["aliases"]:
            token = _squash(alias)
            if len(token) >= 5 and token in squashed:
                return entry["f_number"], _provenance(data, table, entry)

    raise RuleNotFoundError(
        f"No F-number encoded for electrode '{classification}'. Known: "
        + ", ".join(e["aliases"][0] for e in table["electrode_f_numbers"])
    )


def qualified_f_numbers(
    f_number: int,
    backing: Backing,
    path: str | None = None,
) -> tuple[str, Provenance]:
    """Table QW-433 — which filler metals the welder may use in production.

    Raises:
        RuleNotEncodedError: This F-number and backing combination is one of the
            matrix columns that was not recovered from the code. Deliberately
            not inferred from the encoded rows.
    """
    data = load_rules(path)
    table = data["qw_433"]

    for row in table["qualified_with"]:
        if row["f_number"] == f_number and row["backing"] == backing.value:
            with_backing = sorted(
                {q["f_number"] for q in row["qualifies"] if q["backing"] == "with"},
                reverse=True,
            )
            without_backing = sorted(
                {q["f_number"] for q in row["qualifies"] if q["backing"] == "without"},
                reverse=True,
            )
            parts: list[str] = []
            if without_backing:
                joined = ", ".join(f"F-No. {n}" for n in without_backing)
                parts.append(f"{joined} with and without backing")
            only_with = [n for n in with_backing if n not in without_backing]
            if only_with:
                joined = ", ".join(f"F-No. {n}" for n in only_with)
                parts.append(f"{joined} with backing")
            return "; ".join(parts), _provenance(data, table, row)

    raise RuleNotEncodedError(
        f"Table QW-433 row for F-No. {f_number} {backing.value} backing is not "
        "encoded. Only the F-No. 4 columns were recovered from the code; the "
        "rest must be added from the book rather than inferred."
    )


def qualified_backing(backing: Backing, path: str | None = None) -> tuple[str, Provenance]:
    """QW-402.4 — backing qualified by the coupon as welded."""
    data = load_rules(path)
    table = data["qw_402_4"]
    for row in table["rules"]:
        if row["welded"] == backing.value:
            return row["qualified"], _provenance(data, table, row)
    raise RuleNotFoundError(f"QW-402.4 has no rule for backing '{backing.value}'.")


def qualified_progression(
    progression: Progression,
    path: str | None = None,
) -> tuple[str, Provenance]:
    """QW-405.3 — vertical progression qualified."""
    data = load_rules(path)
    table = data["qw_405_3"]
    for row in table["rules"]:
        if row["welded"] == progression.value:
            return row["qualified"], _provenance(data, table, row)
    raise RuleNotFoundError(
        f"QW-405.3 has no rule for progression '{progression.value}'."
    )


def qualified_p_number(p_number: str, path: str | None = None) -> tuple[str, Provenance]:
    """QW-403.18 — base metal P-number range.

    Always raises today: the QW-423 grouping table is not encoded. Kept as a
    real function rather than omitted so the derivation engine reports a
    specific, honest gap instead of quietly having no opinion on an essential
    variable.
    """
    data = load_rules(path)
    table = data["qw_403_18"]
    if not table.get("encoded", False):
        raise RuleNotEncodedError(
            f"QW-403.18 is an essential variable for SMAW but the P-number "
            f"grouping table is not encoded, so no range can be derived for "
            f"'{p_number}'. {table.get('note', '')}"
        )
    raise RuleNotFoundError(f"No P-number rule for '{p_number}'.")  # pragma: no cover


def essential_variables(process: str = "SMAW", path: str | None = None) -> list[dict[str, Any]]:
    """Table QW-353 — the variables a welder requalifies on.

    This is the checklist the derivation engine must produce a range for.
    Anything outside it is recorded for information only.
    """
    data = load_rules(path)
    table = data["essential_variables"]
    if table["process"].upper() != process.upper():
        raise RuleNotEncodedError(
            f"Essential variables are encoded for {table['process']} only, not "
            f"{process}. Table QW-352 to QW-357 cover the other processes."
        )
    return table["variables"]


def unsigned_row_count(path: str | None = None) -> int:
    """How many rule rows still need a reviewer's signature."""
    return _count_unsigned(load_rules(path))


def code_edition(path: str | None = None) -> str:
    return load_rules(path)["code_edition"]


def kb_version(path: str | None = None) -> str:
    return load_rules(path)["kb_version"]
