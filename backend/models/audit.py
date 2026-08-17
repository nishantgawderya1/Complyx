"""Schemas for compliance verdicts.

These are the output of `engines.compliance_checker` and the payload the API
will eventually return. Every parameter result carries the threshold it was
compared against and the clause that threshold came from, so a verdict can be
defended line by line.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ComplianceOutcome(str, Enum):
    """Result of a single comparison, or of a whole document."""

    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    NOT_CHECKED = "NOT_CHECKED"


class ParameterResult(BaseModel):
    """Outcome of comparing one extracted value against one threshold."""

    model_config = ConfigDict(extra="forbid")

    field_name: str
    result: ComplianceOutcome

    extracted_value: float | None = None
    extracted_unit: str | None = None
    normalised_value: float | None = Field(
        default=None, description="Extracted value converted to the canonical unit."
    )

    required_min: float | None = None
    required_max: float | None = None
    unit: str | None = None

    delta: float | None = Field(
        default=None,
        description=(
            "Margin against the breached bound, negative when below a minimum "
            "and positive when above a maximum. None when the check did not run."
        ),
    )

    standard_reference: str | None = None
    page: int | None = None
    source_text: str | None = None
    reason: str | None = Field(
        default=None, description="Why a REVIEW or NOT_CHECKED outcome occurred."
    )


class AuditVerdict(BaseModel):
    """Complete compliance result for one document."""

    # protected_namespaces is cleared so fields may be named model_used etc.
    # "model" here means the LLM, not a Pydantic model.
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    document_name: str
    document_hash: str

    overall_result: ComplianceOutcome
    parameters: list[ParameterResult] = Field(default_factory=list)

    standard_applied: str | None = Field(
        default=None, description='e.g. "ASTM A516/A516M Grade 70".'
    )
    clause_reference: str | None = None
    material_grade_detected: str | None = None
    heat_number: str | None = None

    review_reasons: list[str] = Field(
        default_factory=list,
        description="Why the document needs a human, if it does.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Parse and knowledge-base caveats carried into the verdict.",
    )

    model_used: str | None = Field(
        default=None, description="Model that produced the extraction."
    )
    prompt_version: str | None = Field(
        default=None, description="Prompt version used, for eval traceability."
    )
    knowledge_base_verified: bool = Field(
        default=False,
        description="True when the thresholds applied have been reviewer-checked.",
    )
    extraction_tokens: int | None = Field(
        default=None, description="Total tokens consumed, for cost tracking."
    )

    requires_human_confirmation: bool = Field(
        default=True,
        description=(
            "Always true. No verdict is final until a person confirms it; the "
            "field exists so that the rule is explicit in the payload rather "
            "than implied by convention."
        ),
    )

    @property
    def failed_parameters(self) -> list[ParameterResult]:
        """Parameters that breached a limit."""
        return [p for p in self.parameters if p.result is ComplianceOutcome.FAIL]

    @property
    def review_parameters(self) -> list[ParameterResult]:
        """Parameters that could not be decided automatically."""
        return [p for p in self.parameters if p.result is ComplianceOutcome.REVIEW]
