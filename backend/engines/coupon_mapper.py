"""Map extracted document values onto a CouponInput.

This is the missing middle. `engines/region_extractor.py` produces strings as
they appear on a scan -- `Plate-150*150*16 MM(Thk)`, `Up Hill`, `3G (Uphill)`,
a single-V groove description -- and `engines/derivation.py` consumes a typed
`CouponInput`. Nothing turned one into the other, so the derivation engine could
only ever be called with a hand-built coupon.

## Why this is a typed normaliser layer and not a parser

The cross-document risk found during template work applies here with more force.
The same value reads differently on every document: thickness is `16 mm thk` on
the weld data record and `Plate-150*150*16 MM(Thk)` on the requisition;
progression is `Up Hill` per pass on one and `3G (Uphill)` in a position field
on another. Deriving from raw strings produces wrong ranges, and comparing them
produces false findings.

So every field gets an explicit normaliser with a documented accepted grammar,
and **anything outside that grammar raises rather than resolving to the nearest
plausible reading**. A coupon that does not map routes to REVIEW. It never maps
partially and proceeds, because a defaulted essential variable is
indistinguishable from one that passed once the record is printed.

## What this deliberately does not do

It does not read documents, call a model, or apply any Section IX rule. It turns
strings into types. That keeps it exhaustively testable offline with no key and
no fixtures, which is what makes the derivation path trustworthy end to end.
"""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel, Field

from models.derivation import Backing, CouponForm, CouponInput, Progression

logger = logging.getLogger(__name__)


class UnmappableValueError(ValueError):
    """A value did not match its field's accepted grammar.

    Deliberately an error rather than a None return: the caller must record the
    raw text and route to REVIEW, never substitute a default. A defaulted
    essential variable is the failure mode this whole layer exists to prevent.
    """


class MappingIssue(BaseModel):
    """One field that could not be mapped, and why."""

    field: str
    raw: str | None = None
    reason: str


class CouponMapping(BaseModel):
    """The result of mapping a document's extracted fields onto a coupon."""

    coupon: CouponInput | None = None
    issues: list[MappingIssue] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when a coupon was built and nothing was left unmapped."""
        return self.coupon is not None and not self.issues


# --------------------------------------------------------------------------
# Field normalisers. Each documents the readings it accepts, because that list
# is the contract -- widening it is a deliberate act, not a bug fix.
# --------------------------------------------------------------------------

# "16 mm", "16mm thk", "16 MM(Thk)", "Wall thk: 16 mm thk"
_THICKNESS = re.compile(r"(\d+(?:\.\d+)?)\s*mm", re.IGNORECASE)

# "Plate-150*150*16 MM(Thk)", "Plate 150x150x16mm", "300x150x16mm"
_COUPON_DIMS = re.compile(
    r"(\d+(?:\.\d+)?)\s*[*x×]\s*(\d+(?:\.\d+)?)\s*[*x×]\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

# "Pipe-72mm OD 6mm Thk", "72 mm OD"
_PIPE_OD = re.compile(r"(\d+(?:\.\d+)?)\s*mm\s*OD", re.IGNORECASE)

# "3G", "5F", "2FR", "6G", and combinations like "3G and 4G" / "2G+5G"
_POSITION = re.compile(r"\b([1-6](?:G|FR|F))\b", re.IGNORECASE)


def normalise_thickness_mm(raw: str | None) -> float:
    """Coupon or wall thickness in millimetres.

    Accepts a bare `<n> mm`, and the `L*W*T` coupon-size form printed on the
    requisition, where the **third** dimension is the thickness. A size string
    is checked first: `Plate-150*150*16 MM(Thk)` would otherwise match the 150.
    """
    if not raw or not raw.strip():
        raise UnmappableValueError("thickness is empty")

    dims = _COUPON_DIMS.search(raw)
    if dims:
        return float(dims.group(3))

    match = _THICKNESS.search(raw)
    if match:
        return float(match.group(1))

    raise UnmappableValueError(
        f"cannot read a thickness from {raw!r}; expected '<n> mm' or a "
        "'<length>x<width>x<thickness>' coupon size"
    )


def normalise_coupon_form(raw: str | None, weld_type: str | None = None) -> CouponForm:
    """Which half of Table QW-461.9 applies.

    `raw` names the product form (plate or pipe); `weld_type` the joint (groove
    or fillet). Where the joint is not stated, groove is NOT assumed -- the two
    qualify different positions, so an unstated joint raises.
    """
    if not raw or not raw.strip():
        raise UnmappableValueError("product form is empty")

    text = raw.lower()
    if "plate" in text:
        product = "plate"
    elif "pipe" in text or "tube" in text:
        product = "pipe"
    else:
        raise UnmappableValueError(f"cannot tell plate from pipe in {raw!r}")

    joint_text = (weld_type or raw).lower()
    if "fillet" in joint_text:
        joint = "fillet"
    elif "groove" in joint_text or "butt" in joint_text:
        joint = "groove"
    else:
        raise UnmappableValueError(
            f"cannot tell groove from fillet in {(weld_type or raw)!r}; the two "
            "qualify different positions under QW-461.9, so it is not assumed"
        )

    return CouponForm(f"{product}_{joint}")


def normalise_position(raw: str | None) -> str:
    """Test position, e.g. 3G.

    Tolerates the trailing parenthetical the forms carry -- `3G (Uphill)` -- and
    joins a stated combination into the form Table QW-461.9 keys on.
    """
    if not raw or not raw.strip():
        raise UnmappableValueError("test position is empty")

    found = [m.group(1).upper() for m in _POSITION.finditer(raw)]
    if not found:
        raise UnmappableValueError(
            f"cannot read a welding position from {raw!r}; expected e.g. 3G, 5F, 6G"
        )

    unique: list[str] = []
    for item in found:
        if item not in unique:
            unique.append(item)
    return unique[0] if len(unique) == 1 else "+".join(unique)


def normalise_progression(raw: str | None) -> Progression:
    """Vertical progression.

    Accepts the spaced reading the weld data record prints per pass (`Up Hill`)
    as well as the closed form.
    """
    if not raw or not raw.strip():
        raise UnmappableValueError("progression is empty")

    squashed = re.sub(r"[^a-z]", "", raw.lower())
    if "uphill" in squashed:
        return Progression.UPHILL
    if "downhill" in squashed:
        return Progression.DOWNHILL
    raise UnmappableValueError(
        f"cannot read a vertical progression from {raw!r}; expected uphill or downhill"
    )


def normalise_backing(raw: str | None) -> Backing:
    """Backing, as welded.

    QW-402.4 turns on whether backing was present. Joint descriptions state it
    several ways, and an unrecognised one raises: guessing 'without' hands the
    welder the wider qualification.
    """
    if not raw or not raw.strip():
        raise UnmappableValueError("backing is empty")

    text = raw.lower()
    if (
        "without backing" in text
        or "no backing" in text
        or text.strip() in {"n/a", "na", "nil", "none"}
    ):
        return Backing.WITHOUT
    if "with backing" in text or "backing strip" in text or "backed" in text:
        return Backing.WITH
    # A single-V groove welded from one side carries no backing unless one is
    # named. Stated explicitly rather than inferred from "groove" alone.
    if "single" in text and "groove" in text and "backing" not in text:
        return Backing.WITHOUT
    raise UnmappableValueError(
        f"cannot tell whether {raw!r} was welded with or without backing; "
        "guessing would widen or narrow the qualification"
    )


def count_layers(passes: list[str] | str | None) -> int:
    """Number of weld layers, from the pass list on the weld data record.

    This is the input to QW-452.1(b), and deriving it from the recorded passes
    is better provenance than the tickbox on the WPQR: a pass list is evidence,
    a tick is a mark someone made.
    """
    if passes is None:
        raise UnmappableValueError("no weld passes recorded")

    items = (
        [p for p in re.split(r"[,;/\n]+", passes) if p.strip()]
        if isinstance(passes, str)
        else [p for p in passes if p and str(p).strip()]
    )
    if not items:
        raise UnmappableValueError("weld pass list is empty")
    return len(items)


def normalise_electrode(raw: str | None) -> str:
    """Electrode classification, e.g. E7018.

    Returned as printed rather than canonicalised: `f_number_for_electrode`
    owns the alias table, and duplicating that mapping here would give it two
    places to drift.
    """
    if not raw or not raw.strip():
        raise UnmappableValueError("electrode classification is empty")
    return raw.strip()


def normalise_pipe_diameter_mm(raw: str | None) -> float:
    """Outside diameter in millimetres, for pipe coupons."""
    if not raw or not raw.strip():
        raise UnmappableValueError("pipe diameter is empty")
    match = _PIPE_OD.search(raw) or _THICKNESS.search(raw)
    if match:
        return float(match.group(1))
    raise UnmappableValueError(f"cannot read a pipe outside diameter from {raw!r}")


# --------------------------------------------------------------------------
# The mapper
# --------------------------------------------------------------------------

#: Which extracted field each coupon attribute is read from, in preference
#: order. Several documents state the same value and they do not always agree;
#: reconciliation settles that before mapping, so first-present wins here.
FIELD_SOURCES: dict[str, tuple[str, ...]] = {
    "thickness": ("coupon_size", "wall_thickness", "thickness", "base_metal_thickness"),
    "product_form": ("coupon_size", "product_form", "material_product_form"),
    "weld_type": ("joint_design", "weld_type", "type_of_bevel"),
    "position": ("position", "test_position"),
    "progression": ("direction_of_welding", "progression", "position"),
    "backing": ("backing", "joint_design", "type_of_bevel"),
    "electrode": ("electrode", "filler_metal_type", "filler_metal"),
    "passes": ("weld_passes", "passes"),
    "p_number": ("p_number", "base_metal_p_number", "m1_p_no"),
    "pipe_diameter": ("pipe_size", "pipe_diameter"),
}


def _first_present(
    fields: dict[str, str | None], names: tuple[str, ...]
) -> tuple[str | None, str | None]:
    """Return (field_name, value) for the first name carrying a value."""
    for name in names:
        value = fields.get(name)
        if value is not None and str(value).strip():
            return name, str(value)
    return None, None


def map_coupon(
    fields: dict[str, str | None],
    passes: list[str] | None = None,
    process: str = "SMAW",
) -> CouponMapping:
    """Build a CouponInput from extracted document fields.

    Never raises. Every field that cannot be mapped becomes a `MappingIssue`
    carrying the raw text and the reason, so the caller can show an inspector
    exactly what was unreadable and which document it came from.

    A coupon is returned only when the two attributes Table QW-461.9 is keyed on
    -- product form and test position -- both resolve. Without them there is no
    row to look up, and a partial coupon invites a partial derivation.
    """
    issues: list[MappingIssue] = []

    def attempt(attr: str, fn, *args):
        """Run a normaliser, recording an issue instead of raising."""
        try:
            return fn(*args)
        except UnmappableValueError as exc:
            source, raw = _first_present(fields, FIELD_SOURCES.get(attr, ()))
            issues.append(
                MappingIssue(field=source or attr, raw=raw, reason=f"{attr}: {exc}")
            )
            return None

    _, product_raw = _first_present(fields, FIELD_SOURCES["product_form"])
    _, weld_raw = _first_present(fields, FIELD_SOURCES["weld_type"])
    _, position_raw = _first_present(fields, FIELD_SOURCES["position"])
    _, thickness_raw = _first_present(fields, FIELD_SOURCES["thickness"])
    _, progression_raw = _first_present(fields, FIELD_SOURCES["progression"])
    _, backing_raw = _first_present(fields, FIELD_SOURCES["backing"])
    _, electrode_raw = _first_present(fields, FIELD_SOURCES["electrode"])
    _, diameter_raw = _first_present(fields, FIELD_SOURCES["pipe_diameter"])
    _, p_number_raw = _first_present(fields, FIELD_SOURCES["p_number"])
    _, passes_raw = _first_present(fields, FIELD_SOURCES["passes"])

    coupon_form = attempt("product_form", normalise_coupon_form, product_raw, weld_raw)
    position = attempt("position", normalise_position, position_raw)

    if coupon_form is None or position is None:
        issues.append(
            MappingIssue(
                field="coupon",
                reason=(
                    "Product form and test position are what Table QW-461.9 is "
                    "keyed on. Without both there is no row to look up, so no "
                    "coupon was built and nothing was derived."
                ),
            )
        )
        return CouponMapping(coupon=None, issues=issues)

    thickness = attempt("thickness", normalise_thickness_mm, thickness_raw)
    progression = attempt("progression", normalise_progression, progression_raw)
    backing = attempt("backing", normalise_backing, backing_raw)
    electrode = attempt("electrode", normalise_electrode, electrode_raw)
    layers = attempt(
        "passes", count_layers, passes if passes is not None else passes_raw
    )

    diameter = None
    if coupon_form.value.startswith("pipe"):
        diameter = attempt("pipe_diameter", normalise_pipe_diameter_mm, diameter_raw)

    coupon = CouponInput(
        process=process,
        coupon_form=coupon_form,
        test_position=position,
        thickness_mm=thickness,
        layers=layers,
        electrode_classification=electrode,
        backing=backing,
        progression=progression,
        base_metal_p_number=p_number_raw,
        pipe_diameter_mm=diameter,
    )
    return CouponMapping(coupon=coupon, issues=issues)
