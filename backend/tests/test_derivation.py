"""Tests for Section IX rule lookup and qualified-range derivation.

No document content appears here. The coupon parameters below (3G, 16 mm plate,
E7018, uphill, no backing) are welding parameters, not personal data, and are
the configuration the sample package happens to use.

The most valuable test in this file is `TestGoldenCoupon`: it asserts that the
engine, working only from the encoded code tables, arrives at the same qualified
range a qualified person wrote by hand on the real WPQR. That is an independent
check on both the rule encoding and the derivation logic -- either being wrong
would break it.
"""

import pytest

from engines.derivation import derive
from knowledge_base.section_ix_loader import (
    RuleNotEncodedError,
    RuleNotFoundError,
    essential_variables,
    f_number_for_electrode,
    qualified_backing,
    qualified_f_numbers,
    qualified_positions,
    qualified_progression,
    qualified_thickness,
    required_tests,
    unsigned_row_count,
)
from models.derivation import (
    Backing,
    CouponForm,
    CouponInput,
    DerivationStatus,
    Progression,
)

GOLDEN = CouponInput(
    process="SMAW",
    coupon_form=CouponForm.PLATE_GROOVE,
    test_position="3G",
    thickness_mm=16,
    layers=6,
    electrode_classification="E7018",
    backing=Backing.WITHOUT,
    progression=Progression.UPHILL,
    base_metal_p_number="P1 to P1",
)


class TestPositionTable:
    def test_3g_plate_groove_matches_the_code(self):
        qualified, prov = qualified_positions(CouponForm.PLATE_GROOVE, "3G")
        assert "plate and pipe over 610 mm O.D.: F, V" in qualified
        assert "pipe 610 mm O.D. and under (73 mm O.D. and over): F" in qualified
        assert "Fillet or tack: F, H, V" in qualified
        assert prov.clause_ref == "QW-461.9"

    def test_6g_pipe_qualifies_all_positions(self):
        qualified, _ = qualified_positions(CouponForm.PIPE_GROOVE, "6G")
        assert "All positions" in qualified

    def test_position_is_case_and_space_insensitive(self):
        a, _ = qualified_positions(CouponForm.PLATE_GROOVE, "3g")
        b, _ = qualified_positions(CouponForm.PLATE_GROOVE, " 3G ")
        assert a == b

    def test_fillet_coupon_has_no_groove_range(self):
        qualified, _ = qualified_positions(CouponForm.PLATE_FILLET, "3F")
        assert "Groove" not in qualified
        assert "Fillet or tack: F, H, V" in qualified

    def test_unknown_position_raises_and_names_what_is_encoded(self):
        with pytest.raises(RuleNotFoundError, match="9G"):
            qualified_positions(CouponForm.PLATE_GROOVE, "9G")

    def test_position_valid_for_pipe_is_not_borrowed_for_plate(self):
        # 5G is a pipe position. It must not resolve against a plate coupon
        # just because the letter-number looks plausible.
        with pytest.raises(RuleNotFoundError):
            qualified_positions(CouponForm.PLATE_GROOVE, "5G")


class TestThicknessTables:
    @pytest.mark.parametrize(
        "thickness,side,face,root",
        [
            (6, 0, 1, 1),  # under 10 mm: face and root
            (10, 2, 0, 0),  # band boundary is inclusive at the bottom
            (16, 2, 0, 0),  # the sample coupon
            (18.9, 2, 0, 0),
            (19, 2, 0, 0),  # and exclusive at the top
            (40, 2, 0, 0),
        ],
    )
    def test_required_tests_by_band(self, thickness, side, face, root):
        req = required_tests(thickness)
        assert (req.side_bend, req.face_bend, req.root_bend) == (side, face, root)
        assert req.visual is True

    def test_sample_coupon_requires_two_side_bends(self):
        # The lab report on the real package records exactly this.
        assert required_tests(16).side_bend == 2

    def test_three_layers_on_a_thick_coupon_lifts_the_cap(self):
        qualified, prov = qualified_thickness(16, layers=6)
        assert qualified == "Maximum to be welded"
        assert prov.clause_ref == "QW-452.1(b)"

    def test_fewer_than_three_layers_gives_2t(self):
        qualified, _ = qualified_thickness(16, layers=2)
        assert qualified == "2t = 32 mm"

    def test_thin_coupon_gives_2t_even_with_many_layers(self):
        # The rule needs BOTH >= 13 mm AND three layers.
        qualified, _ = qualified_thickness(10, layers=6)
        assert qualified == "2t = 20 mm"

    def test_unknown_layer_count_on_a_thick_coupon_refuses_to_answer(self):
        # This is the single most consequential call on the form: the answer
        # genuinely differs, so it is not guessed.
        with pytest.raises(RuleNotFoundError, match="layer count is unknown"):
            qualified_thickness(16, layers=None)

    def test_unknown_layer_count_on_a_thin_coupon_is_fine(self):
        # Below 13 mm the layer count cannot change the answer, so it is not
        # needed and withholding an answer would be false caution.
        qualified, _ = qualified_thickness(8, layers=None)
        assert qualified == "2t = 16 mm"


class TestFillerMetal:
    @pytest.mark.parametrize(
        "classification", ["E7018", "E-7018", "e7018", "SFA 5.1 E7018", "SFA5.1E7018"]
    )
    def test_e7018_resolves_to_f4_through_aliases(self, classification):
        f_number, _ = f_number_for_electrode(classification)
        assert f_number == 4

    def test_unknown_electrode_raises_rather_than_nearest_match(self):
        with pytest.raises(RuleNotFoundError):
            f_number_for_electrode("E9999")

    def test_f4_without_backing_matches_the_sample_wpqr(self):
        qualified, prov = qualified_f_numbers(4, Backing.WITHOUT)
        assert "F-No. 4 with and without backing" in qualified
        assert "F-No. 3, F-No. 2, F-No. 1 with backing" in qualified
        assert prov.clause_ref == "QW-433"

    def test_f4_with_backing_does_not_qualify_without_backing(self):
        qualified, _ = qualified_f_numbers(4, Backing.WITH)
        assert "without backing" not in qualified

    def test_unencoded_f_number_column_is_a_distinct_error(self):
        # Only the F-No. 4 columns were recovered from the code. The rest must
        # fail as "not encoded", never be inferred from the encoded rows.
        with pytest.raises(RuleNotEncodedError):
            qualified_f_numbers(5, Backing.WITHOUT)


class TestSimpleVariables:
    def test_without_backing_qualifies_both(self):
        qualified, _ = qualified_backing(Backing.WITHOUT)
        assert qualified == "With and without backing"

    def test_with_backing_qualifies_only_with(self):
        qualified, _ = qualified_backing(Backing.WITH)
        assert qualified == "With backing only"

    def test_uphill_qualifies_uphill_only(self):
        qualified, _ = qualified_progression(Progression.UPHILL)
        assert qualified == "Uphill only"


class TestEssentialVariables:
    def test_smaw_list_matches_table_qw_353(self):
        clauses = {v["clause_ref"] for v in essential_variables("SMAW")}
        assert clauses == {
            "QW-402.4",
            "QW-403.16",
            "QW-403.18",
            "QW-404.15",
            "QW-404.30",
            "QW-405.1",
            "QW-405.3",
        }

    def test_other_processes_are_not_silently_treated_as_smaw(self):
        with pytest.raises(RuleNotEncodedError):
            essential_variables("GTAW")


class TestGoldenCoupon:
    """The engine must reach the same answer a qualified person wrote by hand.

    These expectations come from the real WPQR in the sample package. They are
    welding outcomes, not document content.
    """

    def test_derives_every_variable_the_code_requires(self):
        result = derive(GOLDEN)
        # One row per essential variable in Table QW-353. A variable the engine
        # cannot compute still appears, as an explicit gap.
        assert len(result.variables) == 7

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("backing", "With and without backing"),
            ("thickness", "Maximum to be welded"),
            ("progression", "Uphill only"),
        ],
    )
    def test_matches_the_hand_written_range(self, name, expected):
        result = derive(GOLDEN)
        assert result.by_name(name).qualified == expected

    def test_position_matches_the_hand_written_range(self):
        qualified = derive(GOLDEN).by_name("position").qualified
        assert "F, V" in qualified
        assert "Fillet or tack: F, H, V" in qualified

    def test_filler_matches_the_hand_written_range(self):
        qualified = derive(GOLDEN).by_name("f_number").qualified
        assert "F-No. 4 with and without backing" in qualified

    def test_required_tests_match_the_lab_report(self):
        assert derive(GOLDEN).test_requirement.side_bend == 2

    def test_p_number_is_reported_as_not_encoded_not_guessed(self):
        # QW-423 is not encoded. The variable must appear and say so rather
        # than be absent, which would be indistinguishable from passing.
        p = derive(GOLDEN).by_name("p_number")
        assert p.qualified is None
        assert p.status is DerivationStatus.RULE_NOT_FOUND
        assert "not encoded" in p.reason.lower()

    def test_is_deterministic(self):
        # The same coupon audited twice must produce byte-identical output.
        assert derive(GOLDEN).model_dump_json() == derive(GOLDEN).model_dump_json()


class TestIssuanceGate:
    def test_not_issuable_while_rules_are_unsigned(self):
        # Nothing is reviewer-signed yet, so nothing may be issued to the field
        # however complete it looks.
        assert derive(GOLDEN).issuable is False

    def test_review_reasons_name_every_blocker(self):
        reasons = derive(GOLDEN).review_reasons
        assert len(reasons) == 7
        assert any("not reviewer-signed" in r for r in reasons)
        assert any("p_number" in r for r in reasons)

    def test_missing_input_is_a_result_not_an_exception(self):
        coupon = GOLDEN.model_copy(update={"electrode_classification": None})
        variable = derive(coupon).by_name("f_number")
        assert variable.status is DerivationStatus.INPUT_MISSING
        assert variable.qualified is None

    def test_unreadable_electrode_never_produces_a_range(self):
        coupon = GOLDEN.model_copy(update={"electrode_classification": "E-70I8"})
        variable = derive(coupon).by_name("f_number")
        assert variable.qualified is None
        assert variable.status is DerivationStatus.INPUT_UNRECOGNISED

    def test_missing_layer_count_blocks_the_thickness_range(self):
        coupon = GOLDEN.model_copy(update={"layers": None})
        variable = derive(coupon).by_name("thickness")
        assert variable.qualified is None
        assert "layer count is unknown" in variable.reason

    def test_derive_never_raises_on_a_rule_miss(self):
        empty = CouponInput(coupon_form=CouponForm.PIPE_FILLET, test_position="9Z")
        result = derive(empty)  # must not raise
        assert result.all_derived is False
        assert result.issuable is False


class TestRuleTableHygiene:
    def test_every_row_is_currently_unsigned(self):
        # Guards against a row being marked verified without a reviewer. If a
        # real sign-off lands, this test should be updated deliberately.
        assert unsigned_row_count() > 0

    def test_missing_rule_file_raises(self, tmp_path):
        with pytest.raises(RuleNotFoundError):
            required_tests(16, path=str(tmp_path / "nope.json"))
