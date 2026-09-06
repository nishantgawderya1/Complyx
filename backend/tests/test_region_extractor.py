"""Tests for page geometry and template region extraction.

Test PDFs are generated in-process with PyMuPDF. Welder names and IDs here are
invented -- no real document or crop enters the repository (CLAUDE.md s10).
"""

import fitz
import pytest

from engines.page_geometry import (
    band_text,
    extract_words,
    find_anchor_matches,
    normalise_text,
    resolve_anchor,
    union_bbox,
    words_in_band,
)
from engines.region_extractor import (
    extract_checkbox,
    extract_field,
    extract_page,
    region_pixmap,
    resolve_region,
)
from models.template import (
    AnchorSpec,
    BBox,
    CheckboxSpec,
    FieldSpec,
    FormTemplate,
    FormType,
    ReadMethod,
    RegionSpec,
    ValueKind,
    XMode,
    YMode,
)

PAGE_W = 528.0
PAGE_H = 792.0


def make_page(
    lines: list[tuple[float, float, str]],
    width: float = PAGE_W,
    height: float = PAGE_H,
) -> tuple[fitz.Document, fitz.Page]:
    """Build a one-page PDF from (normalised x, normalised y, text) tuples."""
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    for nx, ny, text in lines:
        page.insert_text((nx * width, ny * height), text, fontsize=9)
    return doc, page


# A miniature of the identity card front: a label column and its values.
CARD_LINES = [
    (0.07, 0.21, "WELDER NAME : TEST WELDER ONE"),
    (0.07, 0.24, "WELDER ID NO.: TPL/TEST/W-01"),
    (0.07, 0.27, "WELDING PROCESS: SMAW"),
]


def name_field(required: bool = True) -> FieldSpec:
    anchor = AnchorSpec(text="WELDER NAME")
    return FieldSpec(
        name="welder_name",
        required=required,
        region=RegionSpec(
            rect=BBox(x0=0.21, y0=0.19, x1=0.70, y1=0.22),
            x_anchor=anchor,
            x_mode=XMode.RIGHT_OF,
            x_width=0.45,
            y_anchor=anchor,
            y_mode=YMode.SAME_ROW,
            y_offset=-0.008,
            y_height=0.020,
        ),
    )


class TestNormaliseText:
    def test_uppercases_and_strips_punctuation(self):
        assert normalise_text("Welder's Name :") == "WELDER S NAME"

    def test_collapses_whitespace(self):
        assert normalise_text("  WELDER   NAME  ") == "WELDER NAME"

    def test_does_not_alter_letters(self):
        # Character-level OCR confusions are handled by explicit `alternates`,
        # never by silently rewriting letters here.
        assert normalise_text("ldentification") == "LDENTIFICATION"


class TestExtractWords:
    def test_returns_normalised_coordinates(self):
        doc, page = make_page(CARD_LINES)
        try:
            words = extract_words(page)
        finally:
            doc.close()

        assert words
        for word in words:
            assert 0.0 <= word.bbox.x0 <= 1.0
            assert 0.0 <= word.bbox.y1 <= 1.0

    def test_sorts_spatially_not_in_pdf_reading_order(self):
        # Written bottom-up; must come back top-down.
        doc, page = make_page([(0.1, 0.8, "LAST"), (0.1, 0.2, "FIRST")])
        try:
            texts = [w.text for w in extract_words(page)]
        finally:
            doc.close()

        assert texts == ["FIRST", "LAST"]

    def test_blank_page_yields_no_words(self):
        doc, page = make_page([])
        try:
            assert extract_words(page) == []
        finally:
            doc.close()


class TestAnchors:
    def test_finds_a_multi_word_anchor_regardless_of_punctuation(self):
        doc, page = make_page(CARD_LINES)
        try:
            matches = find_anchor_matches(extract_words(page), "WELDER NAME")
        finally:
            doc.close()

        assert len(matches) == 1

    def test_occurrence_selects_between_repeated_anchors(self):
        # "Format No." appears once per card face, so the ordinal is
        # load-bearing rather than a tiebreak.
        doc, page = make_page(
            [(0.07, 0.30, "Format No. FRONT"), (0.07, 0.80, "Format No. BACK")]
        )
        try:
            words = extract_words(page)
            first = resolve_anchor(words, "Format No", [], 0)
            second = resolve_anchor(words, "Format No", [], 1)
        finally:
            doc.close()

        assert first is not None and second is not None
        assert first.bbox.y0 < second.bbox.y0

    def test_search_band_isolates_one_face(self):
        doc, page = make_page(
            [(0.07, 0.30, "Format No. FRONT"), (0.07, 0.80, "Format No. BACK")]
        )
        band = BBox(x0=0.0, y0=0.7, x1=1.0, y1=1.0)
        try:
            words = extract_words(page)
            # Within the band there is only one occurrence, so it is index 0.
            found = resolve_anchor(words, "Format No", [], 0, band)
            assert found is not None
            assert found.bbox.y0 > 0.7
        finally:
            doc.close()

    def test_alternates_are_tried_only_after_the_primary_spelling(self):
        doc, page = make_page([(0.07, 0.21, "ldentification of WPS followed")])
        try:
            words = extract_words(page)
            found = resolve_anchor(
                words,
                "Identification of NPS followed",
                ["ldentification of WPS followed"],
                0,
            )
        finally:
            doc.close()

        assert found is not None
        assert found.matched_text == "ldentification of WPS followed"

    def test_missing_anchor_returns_none_rather_than_raising(self):
        doc, page = make_page(CARD_LINES)
        try:
            assert resolve_anchor(extract_words(page), "NOT PRESENT", [], 0) is None
        finally:
            doc.close()

    def test_occurrence_beyond_the_matches_returns_none(self):
        doc, page = make_page(CARD_LINES)
        try:
            assert resolve_anchor(extract_words(page), "WELDER NAME", [], 5) is None
        finally:
            doc.close()


class TestBands:
    def test_words_in_band_uses_centre_containment(self):
        doc, page = make_page(CARD_LINES)
        try:
            words = extract_words(page)
            top = words_in_band(words, BBox(x0=0.0, y0=0.0, x1=1.0, y1=0.22))
            assert any("NAME" in w.text for w in top)
            assert not any("PROCESS" in w.text for w in top)
        finally:
            doc.close()

    def test_band_text_groups_by_visual_row(self):
        doc, page = make_page(CARD_LINES)
        try:
            text = band_text(extract_words(page))
        finally:
            doc.close()

        assert len(text.splitlines()) == 3

    def test_union_bbox_of_nothing_is_none(self):
        assert union_bbox([]) is None


class TestResolveRegion:
    def test_anchor_relative_region_tracks_vertical_drift(self):
        """The design decision this module exists for.

        Two scans of the same form drift by up to 3.6% of page height, and the
        drift grows down the page. A region pinned to a fixed rectangle misses
        the value on the second scan; one pinned to its label follows it.
        """
        spec = name_field().region
        drifted_rect_misses = False

        for offset in (0.0, 0.036):
            lines = [(x, y + offset, t) for x, y, t in CARD_LINES]
            doc, page = make_page(lines)
            try:
                words = extract_words(page)
                region, anchors_used, warnings = resolve_region(words, spec)
                found = " ".join(w.text for w in words_in_band(words, region))

                assert anchors_used == 2
                assert warnings == []
                assert "TEST WELDER ONE" in found

                # The same page read through the declared fallback rect only:
                # at the drifted position the value has moved out of it.
                via_rect = " ".join(
                    w.text for w in words_in_band(words, spec.rect)
                )
                if offset and "TEST" not in via_rect:
                    drifted_rect_misses = True
            finally:
                doc.close()

        assert drifted_rect_misses, (
            "fixed-rect control did not drift out of range; the test no longer "
            "demonstrates why anchor-relative regions are needed"
        )

    def test_falls_back_to_the_rect_when_an_anchor_is_missing(self):
        spec = RegionSpec(
            rect=BBox(x0=0.05, y0=0.19, x1=0.95, y1=0.23),
            x_anchor=AnchorSpec(text="NOT ON THIS PAGE"),
            x_mode=XMode.RIGHT_OF,
            x_width=0.4,
        )
        doc, page = make_page(CARD_LINES)
        try:
            _, anchors_used, warnings = resolve_region(extract_words(page), spec)
        finally:
            doc.close()

        assert anchors_used == 0
        assert warnings and "not found" in warnings[0]

    def test_resolved_region_is_clamped_to_the_page(self):
        spec = RegionSpec(
            rect=BBox(x0=0.9, y0=0.9, x1=1.0, y1=1.0),
            x_anchor=AnchorSpec(text="WELDER NAME"),
            x_mode=XMode.RIGHT_OF,
            x_width=0.95,  # deliberately runs off the right edge
        )
        doc, page = make_page(CARD_LINES)
        try:
            region, _, _ = resolve_region(extract_words(page), spec)
        finally:
            doc.close()

        assert region.x1 <= 1.0
        assert region.y1 <= 1.0


class TestExtractField:
    def test_reads_a_value_and_strips_label_punctuation(self):
        doc, page = make_page(CARD_LINES)
        try:
            field = extract_field(extract_words(page), name_field(), 1, "T/1")
        finally:
            doc.close()

        assert field.value == "TEST WELDER ONE"
        assert field.read_method is ReadMethod.TEMPLATE_REGION
        assert field.confidence == pytest.approx(0.90)
        assert field.needs_review is False
        assert field.template_version == "T/1"
        assert field.page == 1

    def test_bbox_is_the_words_found_not_the_search_region(self):
        doc, page = make_page(CARD_LINES)
        try:
            field = extract_field(extract_words(page), name_field(), 1, "T/1")
        finally:
            doc.close()

        # Provenance the UI highlights: the value, not the box we looked in.
        assert field.bbox is not None
        assert field.bbox.x1 - field.bbox.x0 < 0.45

    def test_missing_required_field_routes_to_review(self):
        spec = FieldSpec(
            name="absent",
            required=True,
            region=RegionSpec(rect=BBox(x0=0.02, y0=0.95, x1=0.10, y1=0.99)),
        )
        doc, page = make_page(CARD_LINES)
        try:
            field = extract_field(extract_words(page), spec, 1, "T/1")
        finally:
            doc.close()

        assert field.value is None
        assert field.needs_review is True
        assert field.confidence == 0.0
        assert "REVIEW" in field.review_reason

    def test_missing_optional_field_does_not_route_to_review(self):
        spec = FieldSpec(
            name="absent",
            required=False,
            region=RegionSpec(rect=BBox(x0=0.02, y0=0.95, x1=0.10, y1=0.99)),
        )
        doc, page = make_page(CARD_LINES)
        try:
            field = extract_field(extract_words(page), spec, 1, "T/1")
        finally:
            doc.close()

        assert field.value is None
        assert field.needs_review is False

    def test_merged_ocr_token_recovers_from_the_rect_and_is_demoted(self):
        # Page 2 of the sample card reads label and value as one word, so the
        # anchor box swallows the value and `right_of` starts past it.
        doc, page = make_page([(0.07, 0.21, "WELDER NAME:TESTWELDER")])
        try:
            field = extract_field(extract_words(page), name_field(), 1, "T/1")
        finally:
            doc.close()

        assert field.value is not None
        assert "TESTWELDER" in field.value
        assert field.read_method is ReadMethod.TEMPLATE_REGION_FALLBACK
        assert field.confidence == pytest.approx(0.40)
        assert field.needs_review is True

    def test_checkbox_field_may_not_be_read_as_text(self):
        spec = FieldSpec(
            name="box",
            value_kind=ValueKind.CHECKBOX,
            region=RegionSpec(rect=BBox(x0=0.1, y0=0.1, x1=0.2, y1=0.2)),
        )
        doc, page = make_page(CARD_LINES)
        try:
            with pytest.raises(ValueError, match="checkbox"):
                extract_field(extract_words(page), spec, 1, "T/1")
        finally:
            doc.close()


class TestExtractCheckbox:
    def test_resolves_regions_but_never_infers_a_value(self):
        # The text layer renders the tick as a stray "v". Reading that would be
        # a third, unsanctioned method; the dual CV/vision read is step 2.
        anchor = AnchorSpec(text="3 layers minimum")
        box = CheckboxSpec(
            name="three_layers",
            clause_ref="QW-452.1(b)",
            yes_region=RegionSpec(
                rect=BBox(x0=0.40, y0=0.20, x1=0.44, y1=0.23),
                x_anchor=anchor,
                x_mode=XMode.RIGHT_OF,
                x_width=0.032,
                y_anchor=anchor,
                y_mode=YMode.SAME_ROW,
                y_height=0.017,
            ),
            no_region=RegionSpec(
                rect=BBox(x0=0.45, y0=0.20, x1=0.49, y1=0.23),
                x_anchor=anchor,
                x_mode=XMode.RIGHT_OF,
                x_offset=0.052,
                x_width=0.032,
                y_anchor=anchor,
                y_mode=YMode.SAME_ROW,
                y_height=0.017,
            ),
        )
        doc, page = make_page([(0.30, 0.21, "3 layers minimum  v Yes    No")])
        try:
            field = extract_checkbox(extract_words(page), box, 1, "T/1")
        finally:
            doc.close()

        assert field.value is None
        assert field.value_kind is ValueKind.CHECKBOX
        assert field.needs_review is True
        assert field.confidence == 0.0
        assert "checkbox_detector" in field.review_reason
        assert field.bbox is not None


class TestExtractPage:
    def _template(self) -> FormTemplate:
        return FormTemplate(
            canonical_key="TF-127-R0",
            form_type=FormType.ID_CARD,
            format_no="NPCIL/QMD/TF-127",
            format_rev="R0",
            template_version="TF-127-R0/1",
            fields=[name_field()],
        )

    def test_reads_every_field_and_flags_the_unverified_template(self):
        doc, page = make_page(CARD_LINES)
        try:
            result = extract_page(page, self._template(), 1)
        finally:
            doc.close()

        assert result.canonical_key == "TF-127-R0"
        assert result.template_verified is False
        assert any("UNVERIFIED" in w for w in result.warnings)
        assert result.by_name("welder_name").value == "TEST WELDER ONE"
        assert result.by_name("nope") is None
        assert result.needs_review is False

    def test_blank_page_reads_nothing_and_says_why(self):
        doc, page = make_page([])
        try:
            result = extract_page(page, self._template(), 1)
        finally:
            doc.close()

        assert result.fields == []
        assert any("no text layer" in w.lower() for w in result.warnings)

    def test_is_deterministic(self):
        template = self._template()
        dumps = []
        for _ in range(3):
            doc, page = make_page(CARD_LINES)
            try:
                dumps.append(extract_page(page, template, 1).model_dump_json())
            finally:
                doc.close()
        assert dumps[0] == dumps[1] == dumps[2]


class TestRegionPixmap:
    def test_crops_the_region_at_the_requested_resolution(self):
        doc, page = make_page(CARD_LINES)
        try:
            pixmap = region_pixmap(
                page, BBox(x0=0.0, y0=0.0, x1=0.5, y1=0.25), dpi=150
            )
        finally:
            doc.close()

        # 0.5 * 528pt = 264pt at 150 DPI -> ~550px, allowing for rounding.
        assert 540 <= pixmap.width <= 560
        assert pixmap.height > 0
