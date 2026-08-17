"""Schemas for LLM-extracted certificate values.

Every value the model reports arrives as an `ExtractedField` carrying its own
provenance -- the page it was read from and the verbatim text it came from --
because a compliance verdict that cannot be traced back to a line of a document
is not defensible to an auditor.

The LLM's raw JSON is validated against these models before anything downstream
touches it. A response that does not fit the schema is rejected rather than
partially trusted.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Confidence(str, Enum):
    """How sure the model is that it read a value correctly."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NOT_FOUND = "not_found"


class DocumentType(str, Enum):
    """Kind of engineering document. Only MTCs are audited in V1."""

    MTC = "MTC"
    WPS = "WPS"
    PQR = "PQR"
    CALIBRATION_CERTIFICATE = "CALIBRATION_CERTIFICATE"
    OTHER = "OTHER"


class ExtractedField(BaseModel):
    """A single value read off the certificate, with its provenance."""

    model_config = ConfigDict(extra="ignore")

    value: float | str | None = None
    unit: str | None = None
    page: int | None = None
    source_text: str | None = None
    confidence: Confidence = Confidence.NOT_FOUND

    @property
    def is_present(self) -> bool:
        """True when the model reported an actual value."""
        return self.value is not None and self.confidence is not Confidence.NOT_FOUND

    @property
    def is_reliable(self) -> bool:
        """True when the value is present and not flagged as a shaky reading.

        Low-confidence values are deliberately excluded: they are routed to a
        human rather than compared, because a misread digit that happens to
        clear a threshold is exactly the silent wrong PASS the product cannot
        afford.
        """
        return self.is_present and self.confidence in (
            Confidence.HIGH,
            Confidence.MEDIUM,
        )

    def as_float(self) -> float | None:
        """Return the value as a number, or None when it is not numeric.

        Handles the common certificate spellings of a number: "265", "265.0",
        "1,350", and ranges/qualifiers like "265 min" which are returned as
        None because they are not a single measured value.
        """
        if self.value is None:
            return None
        if isinstance(self.value, (int, float)):
            return float(self.value)

        text = str(self.value).strip().replace(",", "")
        try:
            return float(text)
        except ValueError:
            return None


def _empty_field() -> ExtractedField:
    return ExtractedField()


class ExtractionResult(BaseModel):
    """Complete structured output for one certificate."""

    model_config = ConfigDict(extra="ignore")

    document_type: DocumentType = DocumentType.OTHER

    specification: ExtractedField = Field(default_factory=_empty_field)
    material_grade: ExtractedField = Field(default_factory=_empty_field)
    heat_number: ExtractedField = Field(default_factory=_empty_field)
    product_form: ExtractedField = Field(default_factory=_empty_field)
    nominal_thickness: ExtractedField = Field(default_factory=_empty_field)

    yield_strength: ExtractedField = Field(default_factory=_empty_field)
    tensile_strength: ExtractedField = Field(default_factory=_empty_field)
    elongation: ExtractedField = Field(default_factory=_empty_field)

    chemical_composition: dict[str, ExtractedField] = Field(default_factory=dict)

    raw_standard_reference: ExtractedField = Field(default_factory=_empty_field)
    uncertain_fields: list[str] = Field(default_factory=list)
    notes: str | None = None

    def mechanical_fields(self) -> dict[str, ExtractedField]:
        """Mechanical properties keyed by field name, in a stable report order."""
        return {
            "yield_strength": self.yield_strength,
            "tensile_strength": self.tensile_strength,
            "elongation": self.elongation,
        }

    @property
    def grade_identifier(self) -> str | None:
        """Best available string for looking the material up in the knowledge base.

        Combines specification and grade when both are present ("ASTM A516" +
        "70"), since either alone is usually ambiguous.
        """
        spec = self.specification.value if self.specification.is_present else None
        grade = self.material_grade.value if self.material_grade.is_present else None

        if spec and grade:
            return f"{spec} {grade}"
        return str(spec or grade) if (spec or grade) else None

    @property
    def has_uncertain_fields(self) -> bool:
        """True when the model flagged any reading as unreliable."""
        if self.uncertain_fields:
            return True
        return any(
            field.confidence is Confidence.LOW
            for field in list(self.mechanical_fields().values())
            + list(self.chemical_composition.values())
        )
