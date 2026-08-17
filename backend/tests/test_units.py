"""Tests for unit normalisation.

Conversion factors are the kind of thing that is silently wrong for months, so
the well-known equivalences are pinned here explicitly.
"""

import pytest

from utils.units import (
    UnknownUnitError,
    is_stress_unit,
    normalise_unit,
    to_mm,
    to_mpa,
    to_percent,
)


class TestNormaliseUnit:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("MPa", "mpa"),
            (" MPA ", "mpa"),
            ("N/mm²", "n/mm2"),
            ("N / mm2", "n/mm2"),
            ("Ksi", "ksi"),
            (None, ""),
        ],
    )
    def test_variants_reduce_to_one_key(self, raw, expected):
        assert normalise_unit(raw) == expected


class TestStressConversion:
    def test_mpa_is_identity(self):
        assert to_mpa(485, "MPa") == 485

    def test_n_per_mm2_equals_mpa(self):
        """N/mm² is numerically identical to MPa; a mill using it is not an error."""
        assert to_mpa(485, "N/mm²") == 485

    def test_ksi_to_mpa(self):
        # 70 ksi is the A516 Gr.70 minimum tensile, published as 485 MPa.
        assert to_mpa(70, "ksi") == pytest.approx(482.6, abs=0.1)

    def test_psi_to_mpa(self):
        assert to_mpa(70000, "psi") == pytest.approx(482.6, abs=0.1)

    def test_kgf_per_mm2_to_mpa(self):
        assert to_mpa(50, "kgf/mm2") == pytest.approx(490.3, abs=0.1)

    def test_unknown_unit_raises_rather_than_defaulting(self):
        """An unrecognised unit must never silently become the canonical one."""
        with pytest.raises(UnknownUnitError):
            to_mpa(485, "bananas")

    def test_missing_unit_raises(self):
        with pytest.raises(UnknownUnitError):
            to_mpa(485, None)

    def test_is_stress_unit_recognises_common_spellings(self):
        assert is_stress_unit("MPa")
        assert is_stress_unit("N/mm²")
        assert is_stress_unit("ksi")
        assert not is_stress_unit("%")
        assert not is_stress_unit(None)


class TestRatioConversion:
    def test_percent_is_identity(self):
        assert to_percent(0.21, "%") == 0.21

    def test_absent_unit_is_treated_as_percent(self):
        """Chemistry tables print bare numbers under a '%' column header."""
        assert to_percent(0.21, None) == 0.21

    def test_ppm_converts_to_percent(self):
        assert to_percent(100, "ppm") == pytest.approx(0.01)

    def test_unknown_ratio_unit_raises(self):
        with pytest.raises(UnknownUnitError):
            to_percent(21, "furlongs")


class TestLengthConversion:
    def test_mm_is_identity(self):
        assert to_mm(12.5, "mm") == 12.5

    def test_inch_to_mm(self):
        assert to_mm(1, "in") == pytest.approx(25.4)
        assert to_mm(0.5, "inch") == pytest.approx(12.7)

    def test_unknown_length_unit_raises(self):
        with pytest.raises(UnknownUnitError):
            to_mm(12, "cubits")
