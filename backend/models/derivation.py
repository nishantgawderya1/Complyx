"""Schemas for Section IX rule lookup and qualified-range derivation.

Every result type here carries three things beyond its value: the clause it came
from, whether the rule row backing it has been signed by a reviewer, and the
page of the code it was read from. That is not bookkeeping -- it is the whole
difference between a number an inspector can sign and a number they cannot.

A derived range with no clause is not a finding, and a derived range from an
unsigned rule row is not issuable. Both states are representable here, and
neither is representable as "fine".
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CouponForm(str, Enum):
    """Which half of Table QW-461.9 a coupon is read from."""

    PLATE_GROOVE = "plate_groove"
    PLATE_FILLET = "plate_fillet"
    PIPE_GROOVE = "pipe_groove"
    PIPE_FILLET = "pipe_fillet"


class Backing(str, Enum):
    WITH = "with"
    WITHOUT = "without"


class Progression(str, Enum):
    UPHILL = "uphill"
    DOWNHILL = "downhill"


class Provenance(BaseModel):
    """Where a rule came from, and whether anyone has signed for it."""

    clause_ref: str
    source_page: int | None = None
    code_edition: str
    kb_version: str
    verified: bool = Field(
        default=False,
        description=(
            "True only when a reviewer has signed this specific rule row. An "
            "unsigned row is usable in development and must be visibly flagged "
            "wherever it is shown."
        ),
    )
    verified_by: str | None = None
    verified_date: str | None = None


class DerivationStatus(str, Enum):
    DERIVED = "derived"
    """A rule was found and applied."""

    RULE_NOT_FOUND = "rule_not_found"
    """No encoded rule covers this input. Routes to REVIEW, never a near match."""

    INPUT_MISSING = "input_missing"
    """A required actual value was not supplied. Routes to REVIEW."""

    INPUT_UNRECOGNISED = "input_unrecognised"
    """The actual value did not resolve through the alias table."""


class DerivedVariable(BaseModel):
    """One QW-350 variable: what was welded, and what that qualifies.

    `qualified` is None whenever `status` is anything but DERIVED. There is no
    representation of "probably this" -- that is the point.
    """

    name: str
    brief: str = ""
    actual: str | None = None
    qualified: str | None = None
    status: DerivationStatus
    reason: str = Field(
        default="",
        description="Human sentence. Why this is the range, or why there isn't one.",
    )
    provenance: Provenance | None = None

    @property
    def is_derived(self) -> bool:
        return self.status is DerivationStatus.DERIVED

    @property
    def needs_review(self) -> bool:
        """True when this row cannot be issued as it stands."""
        return not self.is_derived or not (
            self.provenance and self.provenance.verified
        )


class TestRequirement(BaseModel):
    """What QW-452.1(a) requires for a coupon of a given thickness."""

    visual: bool
    side_bend: int
    face_bend: int
    root_bend: int
    substitution_note: str | None = None
    provenance: Provenance


class CouponInput(BaseModel):
    """The actual values a WPQR is derived from.

    Deliberately a flat set of primitives rather than the extracted-field
    objects: derivation is pure arithmetic over known inputs, and keeping it
    free of extraction concerns is what makes it exhaustively testable offline.
    """

    process: str = "SMAW"
    coupon_form: CouponForm
    test_position: str
    thickness_mm: float | None = None
    layers: int | None = Field(
        default=None,
        description=(
            "Number of weld layers. Derived from the pass count on the weld "
            "data record rather than read from a tickbox where possible."
        ),
    )
    electrode_classification: str | None = None
    backing: Backing | None = None
    progression: Progression | None = None
    base_metal_p_number: str | None = None
    pipe_diameter_mm: float | None = None


class DerivationResult(BaseModel):
    """A full derived qualified range for one coupon."""

    variables: list[DerivedVariable] = Field(default_factory=list)
    test_requirement: TestRequirement | None = None
    code_edition: str
    kb_version: str

    @property
    def all_derived(self) -> bool:
        return all(v.is_derived for v in self.variables)

    @property
    def issuable(self) -> bool:
        """True only when every variable derived from a signed rule row.

        This is the gate on issuing a record. It is deliberately strict: one
        unsigned rule row anywhere means the record is not issuable to the
        field, however good the rest of it looks.
        """
        return bool(self.variables) and all(
            v.is_derived and v.provenance and v.provenance.verified
            for v in self.variables
        )

    def by_name(self, name: str) -> DerivedVariable | None:
        return next((v for v in self.variables if v.name == name), None)

    @property
    def review_reasons(self) -> list[str]:
        """Every reason this result cannot be issued, in order."""
        out: list[str] = []
        for v in self.variables:
            if not v.is_derived:
                out.append(f"{v.name}: {v.reason}")
            elif v.provenance and not v.provenance.verified:
                out.append(
                    f"{v.name}: rule {v.provenance.clause_ref} is not reviewer-signed"
                )
        return out
