"""Tests for format-number canonicalisation and the template registry.

The strings exercised here are format numbers and their OCR misreadings, taken
from the sample packages. They carry no personal data -- no welder name, ID or
photograph appears in this file, and none may. See CLAUDE.md section 10.
"""

import json

import pytest

from knowledge_base.template_registry import (
    TemplateNotFoundError,
    canonical_key,
    canonical_keys,
    get_template,
    known_keys,
    load_registry,
)
from models.template import FormType

# Every reading of a format number observed in the sample packages, paired with
# the key it must resolve to. Five of the six documents are scans whose OCR
# text layer mangles the number differently each time; the sixth (the
# requisition sheet) is born-digital and clean.
OBSERVED_READINGS = [
    # Welder identity card -- four different manglings of one number.
    ("Format No. NPCILQMDITF- 127, Rev.RO", "TF-127-R0"),
    ("Format No. NPCIƯQMDITF- 127, Rev.RO", "TF-127-R0"),
    ("Format No. NPCILUQMDITF- 127, Rev.RO", "TF-127-R0"),
    ("Format No. NPCIUOMD/TF- 127, Rev.RO", "TF-127-R0"),
    ("Format No. NPCIL/QMD/TF-127, Rev.R0", "TF-127-R0"),
    # WPQR -- "0" reads as "D" on page 1 and "/" reads as "I" on page 2.
    ("Form No. FQ/ D69 Rev.2", "FQ-069-R2"),
    ("Form No .FQI069, Rev.2", "FQ-069-R2"),
    ("Form No. FQ/069 Rev.2", "FQ-069-R2"),
    # Requisition sheet -- born-digital, no revision printed.
    ("Format No: NPCIL/QMD/TF/216", "TF-216"),
    # Sample card -- "0" reads as "O".
    ("Format No NPCILIOMDI TFO53 -R1", "TF-053-R1"),
    ("Format No NPCILIQMDI TF053 -R1", "TF-053-R1"),
    # Weld data record -- "F" reads as "E".
    ("Format No: NPCIL/OMD/TE. 114(R0)", "TF-114-R0"),
    ("NPCIL/QMD/TF-114(R0)", "TF-114-R0"),
]

# Text that must never be read as a format number. Most of it is real content
# from the WPQR, which is dense with "No." tokens and QW clause references.
NON_FORMAT_TEXT = [
    "F. No. 4 With & Without Backing",
    "F. No. 3,2 & 1 with Backing",
    "Side Bend (2 No's)",
    "Record No: WQT-139",
    "WQT-138",
    "QW-484",
    "QW-452.1(b)",
    "P1 through P 15F",
    "TEST REPORT",
    "SOFTWARE",
    "the TF of it",
    "",
]


class TestCanonicalKey:
    @pytest.mark.parametrize("raw,expected", OBSERVED_READINGS)
    def test_resolves_every_observed_reading(self, raw, expected):
        assert canonical_key(raw) == expected

    @pytest.mark.parametrize("raw", NON_FORMAT_TEXT)
    def test_rejects_text_that_is_not_a_format_number(self, raw):
        assert canonical_key(raw) is None

    def test_returns_none_for_none(self):
        assert canonical_key(None) is None

    def test_number_is_zero_padded_to_three_digits(self):
        # "FQ/069" and "FQ/69" name the same form; the leading zero is
        # typesetting, not identity.
        assert canonical_key("FQ/69 Rev.2") == canonical_key("FQ/069 Rev.2")

    def test_revision_is_omitted_when_the_form_prints_none(self):
        # Inventing "-R0" would create a distinction the form does not make.
        assert canonical_key("NPCIL/QMD/TF/216") == "TF-216"

    def test_bare_revision_number_normalises_to_r_form(self):
        assert canonical_key("FQ/069 Rev.2") == canonical_key("FQ/069 Rev.R2")

    def test_separator_misread_is_not_absorbed_into_the_number(self):
        # "FQI069" is FQ/069 with the slash read as an I, not FQ-1069.
        # Absorbing it silently misses the template.
        assert canonical_key("FQI069 Rev.2") == "FQ-069-R2"

    def test_leading_letter_twin_in_the_number_is_kept(self):
        # "TFO53" is TF053: the O is a zero, not a separator.
        assert canonical_key("TFO53 -R1") == "TF-053-R1"

    def test_family_token_glued_to_a_mangled_prefix_still_resolves(self):
        # There is no word boundary before the TF in "NPCILQMDITF".
        assert canonical_key("NPCILQMDITF- 127, Rev.RO") == "TF-127-R0"

    def test_unknown_family_token_does_not_resolve(self):
        # An unlisted family must fail loudly rather than match a near twin.
        assert canonical_key("Format No. NPCIL/QMD/XY-127, Rev.R0") is None

    def test_is_deterministic(self):
        # The same page audited twice must produce byte-identical findings.
        for raw, _ in OBSERVED_READINGS:
            assert canonical_key(raw) == canonical_key(raw)


class TestCanonicalKeys:
    def test_collapses_repeats_of_the_same_number(self):
        # The identity card prints its format number on both card faces.
        both_faces = "NPCILQMDITF- 127, Rev.RO ... NPCIUOMD/TF- 127, Rev.RO"
        assert canonical_keys(both_faces) == ["TF-127-R0"]

    def test_reports_two_different_numbers_separately(self):
        mixed = "NPCILQMDITF- 127, Rev.RO and Form No. FQ/ D69 Rev.2"
        assert canonical_keys(mixed) == ["TF-127-R0", "FQ-069-R2"]

    def test_returns_empty_for_text_with_no_format_number(self):
        assert canonical_keys("WELDER IDENTITY CARD") == []


class TestRegistry:
    def test_loads_the_shipped_templates(self):
        registry = load_registry()
        assert "TF-127-R0" in registry
        assert "FQ-069-R2" in registry

    def test_template_form_types(self):
        assert get_template("TF-127-R0").form_type is FormType.ID_CARD
        assert get_template("FQ-069-R2").form_type is FormType.WPQR

    def test_unknown_key_raises_rather_than_returning_none(self):
        # A miss must be surfaced, never treated as "nothing to read".
        with pytest.raises(TemplateNotFoundError):
            get_template("TF-999-R9")

    def test_known_keys_are_sorted(self):
        keys = known_keys()
        assert keys == sorted(keys)

    def test_every_template_declares_a_version_and_a_verified_flag(self):
        for template in load_registry().values():
            assert template.template_version
            # Nothing is reviewer-verified yet; if that changes, the output
            # layer must stop flagging it and this test should be updated
            # deliberately rather than drifting.
            assert template.verified is False

    def test_declared_format_number_agrees_with_the_canonical_key(self):
        for key, template in load_registry().items():
            derived = canonical_key(f"{template.format_no} Rev.{template.format_rev}")
            assert derived == key

    def test_field_names_are_unique_within_a_template(self):
        for template in load_registry().values():
            names = [f.name for f in template.fields] + [
                c.name for c in template.checkboxes
            ]
            assert len(names) == len(set(names))

    def test_rejects_a_template_whose_key_contradicts_its_format_number(self, tmp_path):
        bad = {
            "canonical_key": "TF-999-R0",
            "form_type": "id_card",
            "format_no": "NPCIL/QMD/TF-127",
            "format_rev": "R0",
            "template_version": "bad/1",
            "fields": [],
        }
        (tmp_path / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(TemplateNotFoundError, match="does not match"):
            load_registry(str(tmp_path))

    def test_missing_directory_raises(self, tmp_path):
        with pytest.raises(TemplateNotFoundError):
            load_registry(str(tmp_path / "nope"))

    def test_empty_directory_raises(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(TemplateNotFoundError):
            load_registry(str(empty))
