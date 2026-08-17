"""Audit orchestration.

Ties the four engines together into the one operation the product performs:

    PDF bytes -> parse -> extract -> resolve thresholds -> compare -> verdict

The orchestrator's job is to make sure a problem at any stage becomes a visible
REVIEW rather than a confident answer built on a broken input. An unreadable
scan, an unparseable model response, an unknown grade and an unstated thickness
all end the same way -- a verdict a person has to look at, carrying the reason
why.

Infrastructure failures are treated differently from document problems. A
provider outage raises, because it says nothing about the certificate and
retrying later is the right response. A document the pipeline cannot understand
returns a REVIEW verdict, because that *is* the answer.
"""

from __future__ import annotations

import logging

from engines.compliance_checker import run_compliance_check
from engines.llm_client import ExtractionFailure, LLMClient, LLMError, get_llm_client
from engines.pdf_parser import PdfParseError, parse_document
from knowledge_base.standards_loader import (
    StandardNotFoundError,
    StandardsKnowledgeBase,
    ThicknessOutOfRangeError,
    ThicknessRequiredError,
    get_knowledge_base,
)
from models.audit import AuditVerdict, ComplianceOutcome
from models.document import ParsedDocument
from models.extraction import ExtractionResult
from utils.prompts import ACTIVE_EXTRACTION_PROMPT_VERSION
from utils.units import UnknownUnitError, to_mm

logger = logging.getLogger(__name__)


class AuditError(Exception):
    """An infrastructure failure prevented the audit from running."""


def _review_verdict(
    document_name: str,
    document_hash: str,
    reason: str,
    *,
    warnings: list[str] | None = None,
    grade: str | None = None,
    model_used: str | None = None,
    prompt_version: str | None = None,
) -> AuditVerdict:
    """Build a REVIEW verdict for a document the pipeline could not decide."""
    return AuditVerdict(
        document_name=document_name,
        document_hash=document_hash,
        overall_result=ComplianceOutcome.REVIEW,
        parameters=[],
        material_grade_detected=grade,
        review_reasons=[reason],
        warnings=list(warnings or []),
        model_used=model_used,
        prompt_version=prompt_version,
    )


def _resolve_thickness_mm(extraction: ExtractionResult) -> tuple[float | None, str | None]:
    """Convert the certificate's nominal thickness to millimetres.

    Returns (thickness, warning). A thickness with no unit is not converted:
    the difference between 2 mm and 2 inches decides which requirement band
    applies, and guessing would silently select the wrong limits.
    """
    field = extraction.nominal_thickness

    if not field.is_present:
        return None, None

    value = field.as_float()
    if value is None:
        return None, f"Thickness {field.value!r} is not numeric and was ignored."

    if not field.unit:
        return None, (
            "Thickness was found but its unit was not identified, so it could "
            "not be used to select a requirement band."
        )

    try:
        return to_mm(value, field.unit), None
    except UnknownUnitError as exc:
        return None, f"{exc}. Thickness was ignored."


def audit_document(
    file_bytes: bytes,
    filename: str,
    llm_client: LLMClient | None = None,
    knowledge_base: StandardsKnowledgeBase | None = None,
    prompt_version: str = ACTIVE_EXTRACTION_PROMPT_VERSION,
) -> AuditVerdict:
    """Run the full compliance audit on one document.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename: Original filename, retained for the audit record.
        llm_client: Injected for testing; defaults to the configured client.
        knowledge_base: Injected for testing; defaults to the loaded table.
        prompt_version: Extraction prompt version, recorded on the verdict.

    Returns:
        An `AuditVerdict`. Always requires human confirmation.

    Raises:
        AuditError: The file could not be opened, or the model provider failed.
    """
    client = llm_client or get_llm_client()
    kb = knowledge_base or get_knowledge_base()

    # --- Parse -----------------------------------------------------------
    try:
        parsed: ParsedDocument = parse_document(file_bytes, filename)
    except PdfParseError as exc:
        raise AuditError(str(exc)) from exc

    if not parsed.has_text:
        return _review_verdict(
            filename,
            parsed.document_hash,
            "No text could be recovered from this document, so no values could "
            "be checked.",
            warnings=parsed.warnings,
        )

    # --- Extract ---------------------------------------------------------
    try:
        response = client.extract_structured(parsed.full_text, prompt_version)
    except ExtractionFailure as exc:
        return _review_verdict(
            filename,
            parsed.document_hash,
            f"Values could not be extracted from this document: {exc}",
            warnings=parsed.warnings,
            model_used=client.model_name,
            prompt_version=prompt_version,
        )
    except LLMError as exc:
        raise AuditError(f"Extraction service failure: {exc}") from exc

    extraction = response.result
    warnings = list(parsed.warnings)

    thickness_mm, thickness_warning = _resolve_thickness_mm(extraction)
    if thickness_warning:
        warnings.append(thickness_warning)

    product_form = (
        str(extraction.product_form.value)
        if extraction.product_form.is_present
        else None
    )

    # --- Resolve thresholds ----------------------------------------------
    try:
        thresholds = kb.lookup(
            extraction.grade_identifier,
            product_form=product_form,
            thickness_mm=thickness_mm,
        )
    except StandardNotFoundError as exc:
        return _review_verdict(
            filename,
            parsed.document_hash,
            f"Standard not found: {exc}. No comparison was performed.",
            warnings=warnings,
            grade=extraction.grade_identifier,
            model_used=response.model,
            prompt_version=response.prompt_version,
        )
    except (ThicknessRequiredError, ThicknessOutOfRangeError) as exc:
        return _review_verdict(
            filename,
            parsed.document_hash,
            str(exc),
            warnings=warnings,
            grade=extraction.grade_identifier,
            model_used=response.model,
            prompt_version=response.prompt_version,
        )

    # --- Compare ---------------------------------------------------------
    verdict = run_compliance_check(
        extraction=extraction,
        thresholds=thresholds,
        document_name=filename,
        document_hash=parsed.document_hash,
        parse_warnings=warnings,
        low_quality_source=parsed.is_low_quality,
    )

    verdict.model_used = response.model
    verdict.prompt_version = response.prompt_version
    verdict.knowledge_base_verified = thresholds.verified
    verdict.extraction_tokens = response.total_tokens

    logger.info(
        "Audit complete: %s -> %s (standard=%s, params=%s)",
        filename,
        verdict.overall_result.value,
        verdict.standard_applied,
        len(verdict.parameters),
    )
    return verdict
