"""End-to-end tests for the audit orchestrator.

These run the real pipeline -- real parser, real knowledge base, real comparison
engine -- with only the model call mocked. They are the tests that would catch a
regression in how the stages fit together.
"""

import fitz
import pytest

from engines.doc_auditor import AuditError, audit_document
from engines.llm_client import MockLLMClient
from models.audit import ComplianceOutcome

CERTIFICATE_TEXT = """MATERIAL TEST CERTIFICATE
Specification: ASTM A516/A516M-17  Grade: 70
Heat Number: HT-2891-B
Nominal Thickness: 12 mm
Yield Strength: 265 MPa  Tensile Strength: 480 MPa  Elongation: 24 %
"""


def make_pdf(text: str = CERTIFICATE_TEXT) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


def fld(value, unit=None, confidence="high"):
    return {"value": value, "unit": unit, "page": 1, "confidence": confidence}


def extraction(**overrides):
    payload = {
        "document_type": "MTC",
        "specification": fld("ASTM A516/A516M"),
        "material_grade": fld("70"),
        "heat_number": fld("HT-2891-B"),
        "product_form": fld("plate"),
        "nominal_thickness": fld(12, "mm"),
        "yield_strength": fld(300, "MPa"),
        "tensile_strength": fld(520, "MPa"),
        "elongation": fld(24, "%"),
        "chemical_composition": {
            "C": fld(0.21, "%"),
            "Mn": fld(1.05, "%"),
            "P": fld(0.012, "%"),
            "S": fld(0.008, "%"),
            "Si": fld(0.28, "%"),
        },
        "uncertain_fields": [],
    }
    payload.update(overrides)
    return payload


def audit(payload, pdf: bytes | None = None, name: str = "cert.pdf"):
    return audit_document(
        pdf or make_pdf(), name, llm_client=MockLLMClient(response=payload)
    )


class TestHappyPath:
    def test_conforming_certificate_passes(self):
        verdict = audit(extraction())

        assert verdict.overall_result is ComplianceOutcome.PASS
        assert verdict.standard_applied == "ASTM A516/A516M 70"
        assert verdict.heat_number == "HT-2891-B"
        assert verdict.parameters

    def test_verdict_records_model_and_prompt_version(self):
        """Traceability: a stored result must say what produced it."""
        verdict = audit(extraction())

        assert verdict.model_used == "mock-model"
        assert verdict.prompt_version == "extraction_v1"
        assert verdict.knowledge_base_verified is False

    def test_document_hash_is_recorded(self):
        verdict = audit(extraction())
        assert len(verdict.document_hash) == 64


class TestFailures:
    def test_tensile_below_minimum_fails_with_the_clause_cited(self):
        verdict = audit(extraction(tensile_strength=fld(480, "MPa")))

        assert verdict.overall_result is ComplianceOutcome.FAIL
        failed = verdict.failed_parameters
        assert [p.field_name for p in failed] == ["tensile_strength"]
        assert "A516" in (failed[0].standard_reference or "")
        assert failed[0].delta == pytest.approx(-5)

    def test_carbon_above_maximum_fails(self):
        payload = extraction()
        payload["chemical_composition"]["C"] = fld(0.35, "%")

        verdict = audit(payload)
        assert verdict.overall_result is ComplianceOutcome.FAIL


class TestReviewPaths:
    def test_unknown_grade_reviews_and_does_not_compare(self):
        verdict = audit(
            extraction(specification=fld("ASTM A999"), material_grade=fld("1"))
        )

        assert verdict.overall_result is ComplianceOutcome.REVIEW
        assert verdict.parameters == []
        assert any("not found" in r.lower() for r in verdict.review_reasons)

    def test_missing_thickness_on_a_banded_grade_reviews(self):
        """A516 Gr.70 carbon limits vary by thickness, so the band matters."""
        verdict = audit(
            extraction(nominal_thickness=fld(None, None, confidence="not_found"))
        )

        assert verdict.overall_result is ComplianceOutcome.REVIEW
        assert any("thickness" in r.lower() for r in verdict.review_reasons)

    def test_thickness_without_a_unit_is_not_guessed(self):
        """2 mm and 2 inches select different bands; assuming one is unsafe."""
        verdict = audit(extraction(nominal_thickness=fld(12, None)))

        assert verdict.overall_result is ComplianceOutcome.REVIEW
        assert any("unit" in w.lower() for w in verdict.warnings)

    def test_imperial_certificate_is_converted_and_passes(self):
        verdict = audit(
            extraction(
                nominal_thickness=fld(0.5, "in"),
                yield_strength=fld(45, "ksi"),
                tensile_strength=fld(75, "ksi"),
            )
        )

        assert verdict.overall_result is ComplianceOutcome.PASS
        tensile = next(
            p for p in verdict.parameters if p.field_name == "tensile_strength"
        )
        assert tensile.normalised_value == pytest.approx(517.1, abs=0.5)

    def test_blank_document_reviews_without_calling_the_model(self):
        doc = fitz.open()
        doc.new_page()
        blank = doc.tobytes()
        doc.close()

        client = MockLLMClient(response=extraction())
        verdict = audit_document(blank, "blank.pdf", llm_client=client)

        assert verdict.overall_result is ComplianceOutcome.REVIEW
        assert client.calls == []  # never spent a token on an unreadable file

    def test_unparseable_model_response_reviews_rather_than_raising(self):
        client = MockLLMClient(responses=["garbage", "more garbage"])
        verdict = audit_document(make_pdf(), "cert.pdf", llm_client=client)

        assert verdict.overall_result is ComplianceOutcome.REVIEW
        assert verdict.parameters == []


class TestErrors:
    def test_non_pdf_raises_audit_error(self):
        """A broken upload is an error, not a compliance verdict."""
        with pytest.raises(AuditError):
            audit_document(b"not a pdf", "invoice.txt", llm_client=MockLLMClient())


class TestNeverSilentlyPasses:
    """The property that matters most: no path yields PASS without real checks."""

    @pytest.mark.parametrize(
        "payload",
        [
            extraction(specification=fld("ASTM A999"), material_grade=fld("1")),
            extraction(nominal_thickness=fld(None, None, confidence="not_found")),
            extraction(tensile_strength=fld(520, "MPa", confidence="low")),
            extraction(tensile_strength=fld(520, None)),
            extraction(uncertain_fields=["tensile_strength"]),
        ],
        ids=["unknown-grade", "no-thickness", "low-confidence", "no-unit", "flagged"],
    )
    def test_degraded_inputs_never_pass(self, payload):
        assert audit(payload).overall_result is not ComplianceOutcome.PASS
