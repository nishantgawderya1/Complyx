"""Tests for the typed normaliser layer.

The strings exercised here are welding parameters as they are printed on the
sample forms -- coupon sizes, positions, pass names. They carry no personal
data.

The point of this layer is that it refuses unfamiliar readings rather than
guessing, so roughly half these tests assert that something raises. That is the
intended shape: a normaliser that never rejects anything is a normaliser that
will eventually hand the derivation engine a wrong essential variable.
"""

import pytest

from engines.coupon_mapper import (
    UnmappableValueError,
    count_layers,
    map_coupon,
    normalise_backing,
    normalise_coupon_form,
    normalise_electrode,
    normalise_pipe_diameter_mm,
    normalise_position,
    normalise_progression,
    normalise_thickness_mm,
)
from engines.derivation import derive
from models.derivation import Backing, CouponForm, Progression

# Exactly as they read on the real requisition and weld data record.
REAL_FIELDS = {
    "coupon_size": "Plate-150*150*16 MM(Thk)",
    "joint_design": "Single V Groove",
    "position": "3G (Uphill)",
    "direction_of_welding": "Up Hill",
    "electrode": "E-7018",
    "p_number": "P1",
}
REAL_PASSES = [
    "Root",
    "Stabilizing",
    "Fill up 1",
    "Fill up 2",
    "Fill up 3",
    "Final/Capping",
]


class TestThickness:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("16 mm", 16.0),
            ("16mm thk", 16.0),
            ("Wall thk: 16 mm thk", 16.0),
            ("6mm Thk", 6.0),
            ("12.5 mm", 12.5),
        ],
    )
    def test_reads_a_bare_thickness(self, raw, expected):
        assert normalise_thickness_mm(raw) == expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Plate-150*150*16 MM(Thk)", 16.0),
            ("Plate 150x150x16mm", 16.0),
            ("300x150x16mm", 16.0),
            ("Plate-150*150*10 mm", 10.0),
        ],
    )
    def test_takes_the_third_dimension_of_a_coupon_size(self, raw, expected):
        # The trap: a bare search finds the 150 first.
        assert normalise_thickness_mm(raw) == expected

    @pytest.mark.parametrize("raw", ["", None, "thick", "N/A", "16"])
    def test_rejects_what_it_cannot_read(self, raw):
        with pytest.raises(UnmappableValueError):
            normalise_thickness_mm(raw)


class TestCouponForm:
    def test_plate_groove(self):
        assert (
            normalise_coupon_form("Plate-150*150*16", "Groove")
            is CouponForm.PLATE_GROOVE
        )

    def test_pipe_fillet(self):
        assert (
            normalise_coupon_form("Pipe-72mm OD 6mm Thk", "Fillet")
            is CouponForm.PIPE_FILLET
        )

    def test_joint_may_be_stated_in_the_product_string(self):
        assert normalise_coupon_form("Single V Groove on plate") is CouponForm.PLATE_GROOVE

    def test_unstated_joint_is_not_assumed_to_be_groove(self):
        # Groove and fillet qualify different positions under QW-461.9, so
        # defaulting here would silently change the answer.
        with pytest.raises(UnmappableValueError, match="groove from fillet"):
            normalise_coupon_form("Plate-150*150*16")

    def test_unknown_product_form_raises(self):
        with pytest.raises(UnmappableValueError, match="plate from pipe"):
            normalise_coupon_form("Casting", "Groove")


class TestPosition:
    @pytest.mark.parametrize(
        "raw,expected",
        [("3G", "3G"), ("3G (Uphill)", "3G"), ("5F", "5F"), ("6g", "6G"), ("2FR", "2FR")],
    )
    def test_reads_a_position(self, raw, expected):
        assert normalise_position(raw) == expected

    def test_joins_a_stated_combination(self):
        assert normalise_position("3G and 4G") == "3G+4G"
        assert normalise_position("2G, 3G and 4G") == "2G+3G+4G"

    def test_repeated_position_is_not_a_combination(self):
        assert normalise_position("3G (Uphill) 3G") == "3G"

    @pytest.mark.parametrize("raw", ["", None, "flat", "9G", "G3"])
    def test_rejects_what_it_cannot_read(self, raw):
        with pytest.raises(UnmappableValueError):
            normalise_position(raw)


class TestProgression:
    @pytest.mark.parametrize("raw", ["Up Hill", "UPHILL", "uphill", "3G (Uphill)"])
    def test_reads_uphill_however_it_is_spaced(self, raw):
        assert normalise_progression(raw) is Progression.UPHILL

    def test_reads_downhill(self):
        assert normalise_progression("Down Hill") is Progression.DOWNHILL

    @pytest.mark.parametrize("raw", ["", None, "vertical", "3G"])
    def test_rejects_what_it_cannot_read(self, raw):
        with pytest.raises(UnmappableValueError):
            normalise_progression(raw)


class TestBacking:
    @pytest.mark.parametrize(
        "raw", ["Without backing", "no backing", "N/A", "Single V Groove"]
    )
    def test_reads_without_backing(self, raw):
        assert normalise_backing(raw) is Backing.WITHOUT

    @pytest.mark.parametrize("raw", ["With backing", "backing strip", "Double welded, backed"])
    def test_reads_with_backing(self, raw):
        assert normalise_backing(raw) is Backing.WITH

    def test_ambiguous_backing_raises_rather_than_widening(self):
        # Guessing "without" hands the welder the wider qualification.
        with pytest.raises(UnmappableValueError, match="widen or narrow"):
            normalise_backing("Butt joint")


class TestLayers:
    def test_counts_the_real_pass_list(self):
        assert count_layers(REAL_PASSES) == 6

    def test_accepts_a_delimited_string(self):
        assert count_layers("Root, Fill 1, Fill 2, Capping") == 4

    def test_ignores_blank_entries(self):
        assert count_layers(["Root", "", "  ", "Cap"]) == 2

    @pytest.mark.parametrize("raw", [None, [], "", "   "])
    def test_rejects_an_empty_pass_list(self, raw):
        with pytest.raises(UnmappableValueError):
            count_layers(raw)


class TestMisc:
    def test_electrode_is_returned_as_printed(self):
        # The alias table lives in the rule loader; duplicating it here would
        # give it two places to drift.
        assert normalise_electrode("  E-7018 ") == "E-7018"

    def test_pipe_diameter(self):
        assert normalise_pipe_diameter_mm("Pipe-72mm OD 6mm Thk") == 72.0

    def test_pipe_diameter_rejects_junk(self):
        with pytest.raises(UnmappableValueError):
            normalise_pipe_diameter_mm("large")


class TestMapCoupon:
    def test_maps_the_real_documents_cleanly(self):
        result = map_coupon(REAL_FIELDS, passes=REAL_PASSES)
        assert result.ok
        c = result.coupon
        assert c.coupon_form is CouponForm.PLATE_GROOVE
        assert c.test_position == "3G"
        assert c.thickness_mm == 16.0
        assert c.layers == 6
        assert c.backing is Backing.WITHOUT
        assert c.progression is Progression.UPHILL

    def test_never_raises_on_unreadable_input(self):
        result = map_coupon({"position": "3G", "coupon_size": "Plate x Groove"})
        assert result.coupon is not None  # form and position resolved
        assert result.ok is False  # but thickness did not
        assert any("thickness" in i.reason for i in result.issues)

    def test_no_coupon_without_the_two_keyed_attributes(self):
        # Table QW-461.9 is keyed on product form and position. Without both
        # there is no row, so a partial coupon would invite a partial answer.
        result = map_coupon({"electrode": "E7018"})
        assert result.coupon is None
        assert any("QW-461.9" in i.reason for i in result.issues)

    def test_issues_carry_the_raw_text_for_the_inspector(self):
        result = map_coupon(
            {"coupon_size": "Plate 16mm", "joint_design": "Groove", "position": "3G",
             "direction_of_welding": "sideways"}
        )
        issue = next(i for i in result.issues if "progression" in i.reason)
        assert issue.raw == "sideways"

    def test_is_deterministic(self):
        a = map_coupon(REAL_FIELDS, passes=REAL_PASSES)
        b = map_coupon(REAL_FIELDS, passes=REAL_PASSES)
        assert a.model_dump_json() == b.model_dump_json()


class TestEndToEnd:
    """Documents to qualified range, with no hand-built coupon anywhere.

    This is the chain that did not exist before this module: every engine was
    reachable only from its own tests.
    """

    def test_raw_strings_produce_the_hand_written_range(self):
        mapping = map_coupon(REAL_FIELDS, passes=REAL_PASSES)
        result = derive(mapping.coupon)

        assert result.by_name("backing").qualified == "With and without backing"
        assert result.by_name("thickness").qualified == "Maximum to be welded"
        assert result.by_name("progression").qualified == "Uphill only"
        assert "F, V" in result.by_name("position").qualified
        assert "F-No. 4 with and without backing" in result.by_name("f_number").qualified
        assert result.test_requirement.side_bend == 2

    def test_an_unmapped_thickness_blocks_the_thickness_range(self):
        fields = dict(REAL_FIELDS)
        fields["coupon_size"] = "Plate, groove"  # no thickness in it
        mapping = map_coupon(fields, passes=REAL_PASSES)
        result = derive(mapping.coupon)
        assert result.by_name("thickness").qualified is None

    def test_a_missing_pass_list_blocks_the_thickness_range(self):
        # Without the layer count QW-452.1(b) genuinely has two answers.
        mapping = map_coupon(REAL_FIELDS, passes=None)
        result = derive(mapping.coupon)
        assert result.by_name("thickness").qualified is None
        assert "layer count is unknown" in result.by_name("thickness").reason
