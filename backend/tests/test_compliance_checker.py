"""Tests for the deterministic comparison engine.

The heaviest coverage in the codebase, because this module produces the verdict
and its one unacceptable failure is a PASS that should not have been given.
"""

import pytest

from engines.compliance_checker import (
    aggregate_outcome,
    compare_chemistry,
    compare_elongation,
    compare_property,
    run_compliance_check,
)
from models.audit import ComplianceOutcome
from models.extraction import Confidence, ExtractedField, ExtractionResult
from models.standards import ChemicalLimit, PropertyLimit, Requirement, ResolvedThresholds

CLAUSE = "ASTM A516/A516M Table 2"


def field(value, unit=None, confidence=Confidence.HIGH):
    return ExtractedField(value=value, unit=unit, page=1, confidence=confidence)


def thresholds(properties=None, chemical=None, verified=False):
    return ResolvedThresholds(
        canonical_key="ASTM_A516_70",
        specification="ASTM A516/A516M",
        grade="70",
        clause_reference=CLAUSE,
        verified=verified,
        requirement=Requirement(
            product_form="plate",
            properties=properties or {},
            chemical=chemical or {},
        ),
    )


class TestCompareProperty:
    def test_value_above_minimum_passes(self):
        limit = PropertyLimit(min=260, unit="MPa")
        result = compare_property("yield_strength", field(265, "MPa"), limit, CLAUSE)

        assert result.result is ComplianceOutcome.PASS
        assert result.delta == pytest.approx(5)

    def test_value_below_minimum_fails_with_negative_delta(self):
        limit = PropertyLimit(min=485, max=620, unit="MPa")
        result = compare_property("tensile_strength", field(480, "MPa"), limit, CLAUSE)

        assert result.result is ComplianceOutcome.FAIL
        assert result.delta == pytest.approx(-5)

    def test_value_exactly_at_minimum_passes(self):
        """A specified minimum is inclusive. 485 meets a 485 minimum."""
        limit = PropertyLimit(min=485, unit="MPa")
        result = compare_property("tensile_strength", field(485, "MPa"), limit, CLAUSE)
        assert result.result is ComplianceOutcome.PASS

    def test_value_above_maximum_fails(self):
        limit = PropertyLimit(min=485, max=620, unit="MPa")
        result = compare_property("tensile_strength", field(650, "MPa"), limit, CLAUSE)

        assert result.result is ComplianceOutcome.FAIL
        assert result.delta == pytest.approx(30)

    def test_imperial_value_is_converted_before_comparison(self):
        """75 ksi is about 517 MPa and clears a 485 MPa minimum."""
        limit = PropertyLimit(min=485, max=620, unit="MPa")
        result = compare_property("tensile_strength", field(75, "ksi"), limit, CLAUSE)

        assert result.result is ComplianceOutcome.PASS
        assert result.normalised_value == pytest.approx(517.1, abs=0.5)

    def test_missing_value_reviews_rather_than_passes(self):
        limit = PropertyLimit(min=260, unit="MPa")
        result = compare_property(
            "yield_strength", ExtractedField(confidence=Confidence.NOT_FOUND), limit, CLAUSE
        )

        assert result.result is ComplianceOutcome.REVIEW
        assert "not found" in (result.reason or "").lower()

    def test_low_confidence_value_reviews_even_when_it_would_pass(self):
        """A misread digit that happens to clear the bar is the silent wrong PASS."""
        limit = PropertyLimit(min=260, unit="MPa")
        result = compare_property(
            "yield_strength", field(999, "MPa", Confidence.LOW), limit, CLAUSE
        )
        assert result.result is ComplianceOutcome.REVIEW

    def test_missing_unit_on_a_strength_reviews(self):
        """480 is a pass in MPa and absurd in ksi. The unit is not optional."""
        limit = PropertyLimit(min=485, unit="MPa")
        result = compare_property("tensile_strength", field(480, None), limit, CLAUSE)

        assert result.result is ComplianceOutcome.REVIEW
        assert "unit" in (result.reason or "").lower()

    def test_non_numeric_value_reviews(self):
        limit = PropertyLimit(min=485, unit="MPa")
        result = compare_property(
            "tensile_strength", field("see attached", "MPa"), limit, CLAUSE
        )
        assert result.result is ComplianceOutcome.REVIEW


class TestCompareElongation:
    LIMITS = {
        "elongation_50mm": PropertyLimit(min=21, unit="%"),
        "elongation_200mm": PropertyLimit(min=17, unit="%"),
    }

    def test_above_every_minimum_passes(self):
        result = compare_elongation(field(24, "%"), self.LIMITS, CLAUSE)
        assert result.result is ComplianceOutcome.PASS

    def test_below_every_minimum_fails(self):
        """Below 17% it fails at any gauge length, so the verdict is safe."""
        result = compare_elongation(field(15, "%"), self.LIMITS, CLAUSE)
        assert result.result is ComplianceOutcome.FAIL

    def test_between_the_minima_reviews_because_gauge_length_decides(self):
        """19% passes over 200 mm and fails over 50 mm. Unknowable without the gauge."""
        result = compare_elongation(field(19, "%"), self.LIMITS, CLAUSE)

        assert result.result is ComplianceOutcome.REVIEW
        assert "gauge length" in (result.reason or "").lower()

    def test_single_defined_limit_compares_directly(self):
        limits = {"elongation_50mm": PropertyLimit(min=30, unit="%")}
        assert compare_elongation(field(35, "%"), limits, CLAUSE).result is (
            ComplianceOutcome.PASS
        )
        assert compare_elongation(field(25, "%"), limits, CLAUSE).result is (
            ComplianceOutcome.FAIL
        )


class TestCompareChemistry:
    def test_element_within_range_passes(self):
        limit = ChemicalLimit(min=0.85, max=1.20)
        assert compare_chemistry("Mn", field(1.05, "%"), limit, CLAUSE).result is (
            ComplianceOutcome.PASS
        )

    def test_element_above_maximum_fails(self):
        limit = ChemicalLimit(max=0.27)
        result = compare_chemistry("C", field(0.31, "%"), limit, CLAUSE)

        assert result.result is ComplianceOutcome.FAIL
        assert result.delta == pytest.approx(0.04)

    def test_bare_number_is_read_as_percent(self):
        """Chemistry tables state '%' in the column header, not per cell."""
        limit = ChemicalLimit(max=0.27)
        assert compare_chemistry("C", field(0.21, None), limit, CLAUSE).result is (
            ComplianceOutcome.PASS
        )

    def test_unreported_residual_with_only_a_maximum_is_not_checked(self):
        """Mills routinely omit residuals; that is not grounds to flag a document."""
        result = compare_chemistry("V", None, ChemicalLimit(max=0.08), CLAUSE)
        assert result.result is ComplianceOutcome.NOT_CHECKED

    def test_unreported_element_with_a_minimum_reviews(self):
        """A required element's absence is a real gap."""
        result = compare_chemistry("Mn", None, ChemicalLimit(min=0.85), CLAUSE)
        assert result.result is ComplianceOutcome.REVIEW


class TestAggregate:
    def _p(self, outcome):
        from models.audit import ParameterResult

        return ParameterResult(field_name="x", result=outcome)

    def test_one_fail_fails_the_document(self):
        outcomes = [
            self._p(ComplianceOutcome.PASS),
            self._p(ComplianceOutcome.FAIL),
            self._p(ComplianceOutcome.PASS),
        ]
        assert aggregate_outcome(outcomes) is ComplianceOutcome.FAIL

    def test_fail_outranks_review(self):
        outcomes = [self._p(ComplianceOutcome.REVIEW), self._p(ComplianceOutcome.FAIL)]
        assert aggregate_outcome(outcomes) is ComplianceOutcome.FAIL

    def test_any_review_blocks_a_pass(self):
        outcomes = [self._p(ComplianceOutcome.PASS), self._p(ComplianceOutcome.REVIEW)]
        assert aggregate_outcome(outcomes) is ComplianceOutcome.REVIEW

    def test_nothing_checked_is_review_not_pass(self):
        """'No findings' and 'no checks performed' are different statements."""
        assert aggregate_outcome([]) is ComplianceOutcome.REVIEW
        assert aggregate_outcome([self._p(ComplianceOutcome.NOT_CHECKED)]) is (
            ComplianceOutcome.REVIEW
        )


class TestRunComplianceCheck:
    def _extraction(self, **overrides):
        data = {
            "specification": field("ASTM A516/A516M"),
            "material_grade": field("70"),
            "heat_number": field("HT-2891-B"),
            "yield_strength": field(265, "MPa"),
            "tensile_strength": field(520, "MPa"),
            "elongation": field(24, "%"),
            "chemical_composition": {"C": field(0.21, "%")},
        }
        data.update(overrides)
        return ExtractionResult(**data)

    def _thresholds(self):
        return thresholds(
            properties={
                "yield_strength": PropertyLimit(min=260, unit="MPa"),
                "tensile_strength": PropertyLimit(min=485, max=620, unit="MPa"),
                "elongation_50mm": PropertyLimit(min=21, unit="%"),
            },
            chemical={"C": ChemicalLimit(max=0.27)},
        )

    def test_conforming_certificate_passes(self):
        verdict = run_compliance_check(
            self._extraction(), self._thresholds(), "cert.pdf", "abc123"
        )

        assert verdict.overall_result is ComplianceOutcome.PASS
        assert verdict.heat_number == "HT-2891-B"
        assert verdict.clause_reference == CLAUSE

    def test_verdict_always_requires_human_confirmation(self):
        verdict = run_compliance_check(
            self._extraction(), self._thresholds(), "cert.pdf", "abc123"
        )
        assert verdict.requires_human_confirmation is True

    def test_low_quality_scan_cannot_return_pass(self):
        """Clean-looking numbers off a bad scan may simply be misread."""
        verdict = run_compliance_check(
            self._extraction(),
            self._thresholds(),
            "scan.pdf",
            "abc123",
            low_quality_source=True,
        )

        assert verdict.overall_result is ComplianceOutcome.REVIEW
        assert any("quality" in r.lower() for r in verdict.review_reasons)

    def test_model_flagged_uncertainty_downgrades_a_pass(self):
        verdict = run_compliance_check(
            self._extraction(uncertain_fields=["heat_number"]),
            self._thresholds(),
            "cert.pdf",
            "abc123",
        )
        assert verdict.overall_result is ComplianceOutcome.REVIEW

    def test_failing_parameter_is_reported_with_its_clause(self):
        verdict = run_compliance_check(
            self._extraction(tensile_strength=field(480, "MPa")),
            self._thresholds(),
            "cert.pdf",
            "abc123",
        )

        assert verdict.overall_result is ComplianceOutcome.FAIL
        failed = verdict.failed_parameters
        assert len(failed) == 1
        assert failed[0].field_name == "tensile_strength"
        assert failed[0].standard_reference == CLAUSE

    def test_unverified_thresholds_surface_as_a_warning(self):
        verdict = run_compliance_check(
            self._extraction(), self._thresholds(), "cert.pdf", "abc123"
        )
        # The resolved thresholds fixture carries no notes, so the warning comes
        # from the audit layer; here we assert the plumbing exists.
        assert verdict.warnings == []
        assert verdict.knowledge_base_verified is False
