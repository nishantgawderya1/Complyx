"""Tests for standards knowledge base lookup.

The lookup path decides which thresholds a certificate is judged against. A
wrong match here produces a confident wrong verdict with no visible symptom, so
these tests are deliberately thorough about near-miss grade strings.
"""

import pytest

from knowledge_base.standards_loader import (
    StandardNotFoundError,
    ThicknessRequiredError,
    get_knowledge_base,
    load_standards,
    structural_key,
)


@pytest.fixture(scope="module")
def kb():
    return load_standards()


class TestStructuralKey:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("ASTM A516 Grade 70", "516|70"),
            ("A516 Gr.70", "516|70"),
            ("SA-516 Gr 70", "516|70"),
            ("ASME SA-516 Grade 70", "516|70"),
            ("a516gr70", "516|70"),
            ("ASTM A516/A516M-17 Grade 70", "516|70"),
            ("ASME SA-240 TP304", "240|tp304"),
            ("A240 Type 304", "240|tp304"),
            ("ASTM A312 TP316", "312|tp316"),
            ("A193 B7", "193|b7"),
            ("A106 Gr B", "106|b"),
            ("ASTM A36", "36|-"),
        ],
    )
    def test_spelling_variants_reduce_to_one_key(self, text, expected):
        assert structural_key(text) == expected

    def test_grade_alone_is_not_resolvable(self):
        """"70" without a specification is ambiguous and must not resolve."""
        assert structural_key("Grade 70") is None
        assert structural_key("") is None
        assert structural_key(None) is None


class TestLoad:
    def test_loads_all_ten_v1_grades(self, kb):
        assert len(kb) == 10

    def test_every_entry_is_flagged_unverified(self, kb):
        """Nothing may claim reviewer verification until a reviewer has checked it."""
        assert len(kb.unverified_keys) == len(kb)

    def test_cached_accessor_returns_same_instance(self):
        assert get_knowledge_base() is get_knowledge_base()


class TestFindEntry:
    @pytest.mark.parametrize(
        "text,expected_key",
        [
            ("ASTM A516 Grade 70", "ASTM_A516_70"),
            ("SA-516 Gr.70", "ASTM_A516_70"),
            ("ASTM A516 Grade 60", "ASTM_A516_60"),
            ("A106 Gr B", "ASTM_A106_B"),
            ("ASTM A312 TP304", "ASTM_A312_TP304"),
            ("ASME SA-240 TP304", "ASME_SA240_TP304"),
            ("A193 B7", "ASTM_A193_B7"),
            ("ASTM A36", "ASTM_A36"),
        ],
    )
    def test_resolves_real_certificate_spellings(self, kb, text, expected_key):
        assert kb.find_entry(text).canonical_key == expected_key

    def test_grade_60_and_70_are_never_confused(self, kb):
        """The failure that matters: Gr.60 limits applied to a Gr.70 certificate."""
        assert kb.find_entry("A516 Gr.70").grade == "70"
        assert kb.find_entry("A516 Gr.60").grade == "60"

    def test_a312_and_sa240_304_are_distinct_entries(self, kb):
        """Both are '304' but their chemistry limits differ."""
        pipe = kb.find_entry("ASTM A312 TP304")
        plate = kb.find_entry("ASME SA-240 TP304")
        assert pipe.canonical_key != plate.canonical_key

        pipe_cr = pipe.requirements[0].chemical["Cr"]
        plate_cr = plate.requirements[0].chemical["Cr"]
        assert (pipe_cr.min, pipe_cr.max) != (plate_cr.min, plate_cr.max)

    def test_unknown_grade_raises_rather_than_guessing(self, kb):
        with pytest.raises(StandardNotFoundError):
            kb.find_entry("ASTM A999 Grade 1")

    def test_empty_grade_raises(self, kb):
        with pytest.raises(StandardNotFoundError):
            kb.find_entry(None)


class TestThicknessResolution:
    def test_selects_the_band_covering_the_thickness(self, kb):
        thin = kb.lookup("A516 Gr.70", "plate", 10.0)
        thick = kb.lookup("A516 Gr.70", "plate", 75.0)

        # Mechanical limits are common across bands; carbon is not.
        assert thin.requirement.chemical["C"].max == 0.27
        assert thick.requirement.chemical["C"].max == 0.30
        assert thin.matched_on_thickness is True

    def test_band_boundary_is_inclusive_of_the_upper_bound(self, kb):
        at_boundary = kb.lookup("A516 Gr.70", "plate", 12.5)
        assert at_boundary.requirement.chemical["C"].max == 0.27

    def test_missing_thickness_on_banded_grade_raises(self, kb):
        """Refusing to pick a band is the point: guessing would apply wrong limits."""
        with pytest.raises(ThicknessRequiredError):
            kb.lookup("A516 Gr.70", "plate", None)

    def test_missing_thickness_is_fine_when_limits_do_not_vary(self, kb):
        resolved = kb.lookup("ASTM A312 TP304", "pipe", None)
        assert resolved.requirement.properties["tensile_strength"].min == 515

    def test_a193_b7_strength_falls_with_diameter(self, kb):
        """B7 is the clearest case for qualified thresholds."""
        small = kb.lookup("A193 B7", "bolting", 50.0)
        large = kb.lookup("A193 B7", "bolting", 150.0)

        assert small.requirement.properties["yield_strength"].min == 720
        assert large.requirement.properties["yield_strength"].min == 515


class TestResolvedMetadata:
    def test_unverified_entry_carries_a_note(self, kb):
        resolved = kb.lookup("A516 Gr.70", "plate", 12.0)
        assert resolved.verified is False
        assert any("UNVERIFIED" in note for note in resolved.notes)

    def test_clause_reference_is_always_present(self, kb):
        resolved = kb.lookup("A516 Gr.70", "plate", 12.0)
        assert resolved.clause_reference
