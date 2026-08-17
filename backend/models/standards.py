"""Schemas for the standards knowledge base.

Acceptance limits are **qualified**, not flat. A grade alone does not determine
a threshold: the same material has different minimum yield strengths at
different thicknesses, different limits for plate than for pipe, and different
chemistry allowances for a heat analysis than for a product analysis.

Modelling this as `{grade: {property: {min, max}}}` would produce false FAILs on
conforming material -- which destroys an inspector's trust in the tool just as
fast as a false PASS destroys the product. So a `StandardEntry` holds a list of
`Requirement` blocks, and the loader selects the one matching the certificate's
product form and thickness.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AnalysisBasis(str, Enum):
    """Which chemical analysis a limit applies to.

    Codes commonly permit a wider tolerance on a product (check) analysis than
    on the heat (ladle) analysis. Comparing a product analysis against heat
    limits generates false FAILs on conforming material.
    """

    HEAT = "heat"
    PRODUCT = "product"
    EITHER = "either"


class PropertyLimit(BaseModel):
    """Minimum and/or maximum for one mechanical property."""

    model_config = ConfigDict(extra="forbid")

    min: float | None = None
    max: float | None = None
    unit: str = "MPa"


class ChemicalLimit(BaseModel):
    """Minimum and/or maximum for one chemical element, as a percentage."""

    model_config = ConfigDict(extra="forbid")

    min: float | None = None
    max: float | None = None
    unit: str = "%"
    basis: AnalysisBasis = AnalysisBasis.HEAT


class Requirement(BaseModel):
    """Limits that apply to one product form, condition and thickness band."""

    model_config = ConfigDict(extra="forbid")

    product_form: str = Field(
        default="any",
        description='e.g. "plate", "pipe", "bar", "forging", or "any".',
    )
    condition: str = Field(
        default="any",
        description='Heat-treat condition, e.g. "as-rolled", "normalised", "any".',
    )
    thickness_min_mm: float | None = Field(
        default=None, description="Inclusive lower bound of the thickness band."
    )
    thickness_max_mm: float | None = Field(
        default=None, description="Inclusive upper bound; None means unbounded."
    )

    properties: dict[str, PropertyLimit] = Field(default_factory=dict)
    chemical: dict[str, ChemicalLimit] = Field(default_factory=dict)

    def covers_thickness(self, thickness_mm: float | None) -> bool:
        """True when a thickness falls in this band.

        An unbounded band matches anything. An unknown thickness matches only an
        unbounded band -- guessing which band applies is exactly the kind of
        silent assumption that produces a wrong verdict.
        """
        if self.thickness_min_mm is None and self.thickness_max_mm is None:
            return True
        if thickness_mm is None:
            return False
        if self.thickness_min_mm is not None and thickness_mm < self.thickness_min_mm:
            return False
        if self.thickness_max_mm is not None and thickness_mm > self.thickness_max_mm:
            return False
        return True

    def covers_form(self, product_form: str | None) -> bool:
        """True when this requirement applies to the given product form."""
        if self.product_form == "any":
            return True
        if not product_form:
            return False
        return self.product_form.strip().lower() == product_form.strip().lower()


class StandardEntry(BaseModel):
    """One material grade and every requirement block defined for it."""

    model_config = ConfigDict(extra="forbid")

    specification: str = Field(..., description='e.g. "ASTM A516/A516M".')
    grade: str = Field(..., description='e.g. "70".')
    canonical_key: str = Field(..., description='Stable id, e.g. "ASTM_A516_70".')
    aliases: list[str] = Field(
        default_factory=list,
        description="Lowercased spellings seen on real certificates.",
    )
    clause_reference: str = Field(
        ..., description='Cited on every verdict, e.g. "ASTM A516/A516M Table 2".'
    )
    source: str = Field(
        ..., description="Where these numbers came from. Required for auditability."
    )
    verified: bool = Field(
        default=False,
        description=(
            "True only once a qualified reviewer has checked these values "
            "against the governing code. Unverified entries must not back a "
            "verdict shown to a real inspector."
        ),
    )
    requirements: list[Requirement] = Field(default_factory=list)


class ResolvedThresholds(BaseModel):
    """The single requirement block selected for a specific certificate."""

    model_config = ConfigDict(extra="forbid")

    canonical_key: str
    specification: str
    grade: str
    clause_reference: str
    verified: bool
    requirement: Requirement
    matched_on_thickness: bool = Field(
        default=False,
        description="True when a thickness-qualified band was selected.",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Caveats to surface on the verdict, e.g. an unverified table.",
    )
