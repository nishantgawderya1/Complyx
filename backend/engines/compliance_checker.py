"""Deterministic compliance comparison.

No AI in this module, by design. Deciding whether 265 MPa clears a 260 MPa
minimum is arithmetic; routing it through a language model would add latency,
cost and a hallucination risk in exchange for nothing. The LLM reports what the
certificate says, and this module decides what that means.

The governing principle is that the engine never guesses. A missing value, an
unidentified unit, a reading the model flagged as shaky, or an ambiguous gauge
length all produce REVIEW -- a handoff to a person -- rather than an assumed
PASS. A wrong FAIL costs an inspector five minutes; a wrong PASS is the failure
mode that ends the product.
"""

from __future__ import annotations

import logging

from models.audit import AuditVerdict, ComplianceOutcome, ParameterResult
from models.extraction import ExtractedField, ExtractionResult
from models.standards import ChemicalLimit, PropertyLimit, ResolvedThresholds
from utils.units import UnknownUnitError, is_stress_unit, to_mpa, to_percent

logger = logging.getLogger(__name__)

# Elongation limits differ by gauge length. A certificate that does not state
# its gauge length cannot be compared against a single one of them.
_ELONGATION_KEYS = ("elongation_50mm", "elongation_200mm")

# Floating point tolerance. A value exactly at the limit passes -- a specified
# minimum is inclusive -- and this keeps 484.99999 from failing a 485 minimum.
_EPSILON = 1e-9


def _normalise_stress(field: ExtractedField) -> tuple[float | None, str | None]:
    """Convert a strength reading to MPa.

    Returns (value, error). A missing unit is an error, not an assumption: a
    bare "480" is 480 MPa or 480 ksi depending on the mill, and the difference
    decides the verdict.
    """
    value = field.as_float()
    if value is None:
        return None, "Value is not numeric"

    if not field.unit:
        return None, "Unit not identified on the certificate"

    if not is_stress_unit(field.unit):
        return None, f"Unrecognised unit {field.unit!r}"

    try:
        return to_mpa(value, field.unit), None
    except UnknownUnitError as exc:
        return None, str(exc)


def _normalise_ratio(field: ExtractedField) -> tuple[float | None, str | None]:
    """Convert an elongation or chemistry reading to percent.

    Unlike strengths, a missing unit is accepted here: chemistry and elongation
    tables state percent in the column header, and a bare number under a "%"
    heading is unambiguous.
    """
    value = field.as_float()
    if value is None:
        return None, "Value is not numeric"

    try:
        return to_percent(value, field.unit), None
    except UnknownUnitError as exc:
        return None, str(exc)


def _review(
    field_name: str,
    reason: str,
    field: ExtractedField | None = None,
    clause: str | None = None,
) -> ParameterResult:
    """Build a REVIEW result carrying the reason a human is needed."""
    return ParameterResult(
        field_name=field_name,
        result=ComplianceOutcome.REVIEW,
        extracted_value=field.as_float() if field else None,
        extracted_unit=field.unit if field else None,
        page=field.page if field else None,
        source_text=field.source_text if field else None,
        standard_reference=clause,
        reason=reason,
    )


def _compare_bounds(
    field_name: str,
    field: ExtractedField,
    normalised: float,
    minimum: float | None,
    maximum: float | None,
    unit: str,
    clause: str,
) -> ParameterResult:
    """Apply minimum and maximum bounds to an already-normalised value."""
    result = ComplianceOutcome.PASS
    delta: float | None = None

    if minimum is not None and normalised < minimum - _EPSILON:
        result = ComplianceOutcome.FAIL
        delta = normalised - minimum
    elif maximum is not None and normalised > maximum + _EPSILON:
        result = ComplianceOutcome.FAIL
        delta = normalised - maximum
    elif minimum is not None:
        delta = normalised - minimum
    elif maximum is not None:
        delta = normalised - maximum

    return ParameterResult(
        field_name=field_name,
        result=result,
        extracted_value=field.as_float(),
        extracted_unit=field.unit,
        normalised_value=normalised,
        required_min=minimum,
        required_max=maximum,
        unit=unit,
        delta=delta,
        standard_reference=clause,
        page=field.page,
        source_text=field.source_text,
    )


def compare_property(
    field_name: str,
    field: ExtractedField,
    limit: PropertyLimit,
    clause: str,
) -> ParameterResult:
    """Compare one mechanical property against its limit."""
    if not field.is_present:
        return _review(field_name, "Value not found in document", field, clause)

    if not field.is_reliable:
        return _review(
            field_name,
            "Model flagged this reading as low confidence",
            field,
            clause,
        )

    is_stress = limit.unit.lower() not in {"%", "pct", "percent"}
    normalised, error = (
        _normalise_stress(field) if is_stress else _normalise_ratio(field)
    )

    if normalised is None:
        return _review(field_name, error or "Value could not be normalised", field, clause)

    return _compare_bounds(
        field_name, field, normalised, limit.min, limit.max, limit.unit, clause
    )


def compare_elongation(
    field: ExtractedField,
    limits: dict[str, PropertyLimit],
    clause: str,
) -> ParameterResult:
    """Compare elongation when the applicable gauge length is unknown.

    Codes specify different minimum elongations for different gauge lengths --
    typically a lower figure over 200 mm than over 50 mm. Certificates do not
    always say which they measured.

    Rather than guess, the comparison brackets it:

    * below every defined minimum  -> FAIL, true regardless of gauge length
    * at or above every minimum    -> PASS, true regardless of gauge length
    * in between                   -> REVIEW, the verdict depends on which
                                      gauge length was used

    This cannot produce a wrong verdict from an unstated gauge length.
    """
    defined = {k: v for k, v in limits.items() if v.min is not None}

    if len(defined) <= 1:
        key, limit = next(iter(defined.items()), ("elongation", PropertyLimit(unit="%")))
        return compare_property(key, field, limit, clause)

    if not field.is_present:
        return _review("elongation", "Value not found in document", field, clause)
    if not field.is_reliable:
        return _review(
            "elongation", "Model flagged this reading as low confidence", field, clause
        )

    normalised, error = _normalise_ratio(field)
    if normalised is None:
        return _review("elongation", error or "Value could not be normalised", field, clause)

    minima = {k: v.min for k, v in defined.items()}
    lowest = min(minima.values())  # type: ignore[type-var]
    highest = max(minima.values())  # type: ignore[type-var]

    if normalised < lowest - _EPSILON:
        return ParameterResult(
            field_name="elongation",
            result=ComplianceOutcome.FAIL,
            extracted_value=field.as_float(),
            extracted_unit=field.unit,
            normalised_value=normalised,
            required_min=lowest,
            unit="%",
            delta=normalised - lowest,
            standard_reference=clause,
            page=field.page,
            source_text=field.source_text,
            reason="Below the minimum for every defined gauge length",
        )

    if normalised >= highest - _EPSILON:
        return ParameterResult(
            field_name="elongation",
            result=ComplianceOutcome.PASS,
            extracted_value=field.as_float(),
            extracted_unit=field.unit,
            normalised_value=normalised,
            required_min=highest,
            unit="%",
            delta=normalised - highest,
            standard_reference=clause,
            page=field.page,
            source_text=field.source_text,
        )

    detail = ", ".join(f"{k}: {v}%" for k, v in sorted(minima.items()))
    return _review(
        "elongation",
        (
            f"Gauge length not identified on the certificate. {normalised}% meets "
            f"some but not all defined minima ({detail}), so the verdict depends "
            "on which gauge length was measured."
        ),
        field,
        clause,
    )


def compare_chemistry(
    element: str,
    field: ExtractedField | None,
    limit: ChemicalLimit,
    clause: str,
) -> ParameterResult:
    """Compare one chemical element against its limit.

    An element the certificate does not report is handled by what the code asks
    of it. If the specification sets a minimum, the absence matters and the
    document goes to review. If it sets only a maximum -- typical of residual
    elements -- mills routinely omit it, so the check is recorded as not
    performed rather than flagged, and it does not affect the verdict.
    """
    field_name = f"chemical.{element}"

    if field is None or not field.is_present:
        if limit.min is not None:
            return _review(
                field_name,
                f"{element} not reported, but the specification sets a minimum",
                field,
                clause,
            )
        return ParameterResult(
            field_name=field_name,
            result=ComplianceOutcome.NOT_CHECKED,
            required_max=limit.max,
            unit=limit.unit,
            standard_reference=clause,
            reason=(
                f"{element} not reported on the certificate; specification "
                "defines a maximum only"
            ),
        )

    if not field.is_reliable:
        return _review(
            field_name, "Model flagged this reading as low confidence", field, clause
        )

    normalised, error = _normalise_ratio(field)
    if normalised is None:
        return _review(field_name, error or "Value could not be normalised", field, clause)

    return _compare_bounds(
        field_name, field, normalised, limit.min, limit.max, limit.unit, clause
    )


def aggregate_outcome(parameters: list[ParameterResult]) -> ComplianceOutcome:
    """Reduce parameter results to one document verdict.

    One FAIL fails the document. Any unresolved parameter forces REVIEW. A
    document where nothing could be checked is REVIEW, never PASS -- "no
    findings" and "no checks performed" are different statements.
    """
    if any(p.result is ComplianceOutcome.FAIL for p in parameters):
        return ComplianceOutcome.FAIL
    if any(p.result is ComplianceOutcome.REVIEW for p in parameters):
        return ComplianceOutcome.REVIEW
    if any(p.result is ComplianceOutcome.PASS for p in parameters):
        return ComplianceOutcome.PASS
    return ComplianceOutcome.REVIEW


def run_compliance_check(
    extraction: ExtractionResult,
    thresholds: ResolvedThresholds,
    document_name: str,
    document_hash: str,
    parse_warnings: list[str] | None = None,
    low_quality_source: bool = False,
) -> AuditVerdict:
    """Compare every extracted value against the resolved thresholds.

    Args:
        extraction: Validated LLM output.
        thresholds: The requirement block selected for this certificate.
        document_name: Original filename, for the audit record.
        document_hash: SHA-256 of the source file.
        parse_warnings: Warnings raised by the PDF parser.
        low_quality_source: True when the source was a poor scan. Such a
            document can never return PASS, however clean the numbers look --
            the numbers themselves may be misread.
    """
    clause = thresholds.clause_reference
    requirement = thresholds.requirement
    parameters: list[ParameterResult] = []

    mechanical = extraction.mechanical_fields()

    for field_name in ("yield_strength", "tensile_strength"):
        limit = requirement.properties.get(field_name)
        if limit is None:
            continue
        parameters.append(
            compare_property(field_name, mechanical[field_name], limit, clause)
        )

    elongation_limits = {
        key: requirement.properties[key]
        for key in _ELONGATION_KEYS
        if key in requirement.properties
    }
    if elongation_limits:
        parameters.append(
            compare_elongation(extraction.elongation, elongation_limits, clause)
        )

    for element, limit in requirement.chemical.items():
        parameters.append(
            compare_chemistry(
                element, extraction.chemical_composition.get(element), limit, clause
            )
        )

    overall = aggregate_outcome(parameters)

    review_reasons = [
        f"{p.field_name}: {p.reason}"
        for p in parameters
        if p.result is ComplianceOutcome.REVIEW and p.reason
    ]

    warnings = list(parse_warnings or [])
    warnings.extend(thresholds.notes)

    if extraction.uncertain_fields:
        review_reasons.append(
            "Model flagged fields as uncertain: "
            + ", ".join(extraction.uncertain_fields)
        )
        if overall is ComplianceOutcome.PASS:
            overall = ComplianceOutcome.REVIEW

    if low_quality_source and overall is ComplianceOutcome.PASS:
        overall = ComplianceOutcome.REVIEW
        review_reasons.append(
            "Source document quality is too low to certify a PASS; values may "
            "have been misread."
        )

    if extraction.notes:
        warnings.append(f"Extraction note: {extraction.notes}")

    return AuditVerdict(
        document_name=document_name,
        document_hash=document_hash,
        overall_result=overall,
        parameters=parameters,
        standard_applied=f"{thresholds.specification} {thresholds.grade}".strip(),
        clause_reference=clause,
        material_grade_detected=extraction.grade_identifier,
        heat_number=(
            str(extraction.heat_number.value)
            if extraction.heat_number.is_present
            else None
        ),
        review_reasons=review_reasons,
        warnings=warnings,
    )
