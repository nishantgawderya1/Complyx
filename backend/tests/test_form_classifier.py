"""Tests for the form classifier.

Test PDFs are generated in-process with PyMuPDF. No real document, crop or
photograph enters the repository -- the sample packages carry welder
photographs, names and ID numbers from an operating nuclear site (CLAUDE.md
section 10). The welder names below are invented.
"""

import fitz
import pytest

from engines.form_classifier import classify_document, classify_page
from models.template import ClassificationOutcome, FormType


def make_form(
    lines: list[tuple[float, float, str]],
    width: float = 528.0,
    height: float = 792.0,
) -> bytes:
    """Build a one-page PDF with text at given normalised positions.

    `lines` are (x, y, text) with x and y as fractions of page width/height, so
    a test can state layout the same way a template does.
    """
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    for nx, ny, text in lines:
        page.insert_text((nx * width, ny * height), text, fontsize=9)
    data = doc.tobytes()
    doc.close()
    return data


def first_page(pdf_bytes: bytes) -> tuple[fitz.Document, fitz.Page]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return doc, doc.load_page(0)


ID_CARD_LINES = [
    (0.33, 0.09, "WELDER IDENTITY CARD"),
    (0.07, 0.21, "WELDER NAME : TEST WELDER ONE"),
    (0.07, 0.24, "WELDER ID NO.: TPL/TEST/W-01"),
    (0.07, 0.27, "WELDING PROCESS: SMAW"),
    (0.07, 0.30, "VALIDITY: TILL SATISFACTORY PERFORMANCE"),
    (0.07, 0.46, "Format No. NPCIL/QMD/TF-127, Rev.R0"),
]


class TestClassifyPage:
    def test_matches_a_known_form(self):
        doc, page = first_page(make_form(ID_CARD_LINES))
        try:
            result = classify_page(page, 1)
        finally:
            doc.close()

        assert result.outcome is ClassificationOutcome.MATCHED
        assert result.canonical_key == "TF-127-R0"
        assert result.form_type is FormType.ID_CARD
        assert result.template_version == "TF-127-R0/1"
        assert result.matched is True

    def test_matches_through_a_mangled_ocr_reading(self):
        mangled = [*ID_CARD_LINES[:-1], (0.07, 0.46, "Format No. NPCILQMDITF- 127, Rev.RO")]
        doc, page = first_page(make_form(mangled))
        try:
            result = classify_page(page, 1)
        finally:
            doc.close()

        assert result.canonical_key == "TF-127-R0"

    def test_signature_tokens_raise_confidence(self):
        with_tokens = make_form(ID_CARD_LINES)
        without_tokens = make_form(
            [(0.07, 0.46, "Format No. NPCIL/QMD/TF-127, Rev.R0")]
        )

        doc_a, page_a = first_page(with_tokens)
        doc_b, page_b = first_page(without_tokens)
        try:
            rich = classify_page(page_a, 1)
            bare = classify_page(page_b, 1)
        finally:
            doc_a.close()
            doc_b.close()

        assert rich.matched and bare.matched
        assert rich.confidence > bare.confidence
        assert "WELDER IDENTITY CARD" in rich.matched_signature_tokens
        assert bare.matched_signature_tokens == []

    def test_never_reports_certainty(self):
        doc, page = first_page(make_form(ID_CARD_LINES))
        try:
            result = classify_page(page, 1)
        finally:
            doc.close()
        assert result.confidence < 1.0

    def test_signature_tokens_alone_do_not_classify(self):
        # Title text gets copied between forms. Only the format number decides.
        titles_only = [
            (0.33, 0.09, "WELDER IDENTITY CARD"),
            (0.07, 0.30, "VALIDITY: TILL SATISFACTORY PERFORMANCE"),
            (0.47, 0.53, "BACK SIDE"),
        ]
        doc, page = first_page(make_form(titles_only))
        try:
            result = classify_page(page, 1)
        finally:
            doc.close()

        assert result.outcome is ClassificationOutcome.TEMPLATE_UNKNOWN
        assert result.canonical_key is None

    def test_unregistered_format_number_reports_unknown_with_the_key(self):
        # TF-216 canonicalises fine but has no template yet. The reason must
        # say so, and name what is registered, so the gap is visible.
        doc, page = first_page(make_form([(0.07, 0.03, "Format No: NPCIL/QMD/TF/216")]))
        try:
            result = classify_page(page, 1)
        finally:
            doc.close()

        assert result.outcome is ClassificationOutcome.TEMPLATE_UNKNOWN
        assert result.canonical_candidates == ["TF-216"]
        assert "TF-216" in result.reason
        assert "TF-127-R0" in result.reason

    def test_two_different_format_numbers_are_ambiguous_not_a_tiebreak(self):
        doc, page = first_page(
            make_form(
                [
                    (0.07, 0.05, "Format No. NPCIL/QMD/TF-127, Rev.R0"),
                    (0.07, 0.08, "Form No. FQ/069 Rev.2"),
                ]
            )
        )
        try:
            result = classify_page(page, 1)
        finally:
            doc.close()

        assert result.outcome is ClassificationOutcome.AMBIGUOUS
        assert result.canonical_key is None
        assert sorted(result.canonical_candidates) == ["FQ-069-R2", "TF-127-R0"]

    def test_repeated_same_format_number_is_not_ambiguous(self):
        # The identity card prints its number once per card face.
        doc, page = first_page(
            make_form(
                [
                    *ID_CARD_LINES,
                    (0.09, 0.91, "Format No. NPCIƯQMDITF- 127, Rev.RO"),
                ]
            )
        )
        try:
            result = classify_page(page, 1)
        finally:
            doc.close()

        assert result.outcome is ClassificationOutcome.MATCHED
        assert result.canonical_key == "TF-127-R0"

    def test_blank_page_reports_unknown_and_says_why(self):
        doc, page = first_page(make_form([]))
        try:
            result = classify_page(page, 1)
        finally:
            doc.close()

        assert result.outcome is ClassificationOutcome.TEMPLATE_UNKNOWN
        assert "no text layer" in result.reason.lower()

    def test_records_which_band_the_number_was_found_in(self):
        header = make_form([(0.07, 0.03, "Format No. NPCIL/QMD/TF-127, Rev.R0")])
        footer = make_form([(0.07, 0.90, "Format No. NPCIL/QMD/TF-127, Rev.R0")])

        doc_a, page_a = first_page(header)
        doc_b, page_b = first_page(footer)
        try:
            assert classify_page(page_a, 1).found_in_band == "header"
            assert classify_page(page_b, 1).found_in_band == "footer"
        finally:
            doc_a.close()
            doc_b.close()

    def test_reports_the_raw_reading_and_its_position_as_provenance(self):
        doc, page = first_page(make_form(ID_CARD_LINES))
        try:
            result = classify_page(page, 1)
        finally:
            doc.close()

        assert result.raw_format_text is not None
        assert "127" in result.raw_format_text
        assert result.bbox is not None
        assert 0.0 <= result.bbox.y0 <= 1.0

    def test_flags_an_unverified_template(self):
        doc, page = first_page(make_form(ID_CARD_LINES))
        try:
            result = classify_page(page, 1)
        finally:
            doc.close()

        assert result.template_verified is False
        assert "UNVERIFIED" in result.reason

    def test_survives_a_different_page_size(self):
        # The same card scans to 528x792 and 542x792 points.
        for width in (528.0, 541.9, 612.0):
            doc, page = first_page(make_form(ID_CARD_LINES, width=width))
            try:
                assert classify_page(page, 1).canonical_key == "TF-127-R0"
            finally:
                doc.close()

    def test_is_deterministic(self):
        pdf = make_form(ID_CARD_LINES)
        results = []
        for _ in range(3):
            doc, page = first_page(pdf)
            try:
                results.append(classify_page(page, 1).model_dump_json())
            finally:
                doc.close()
        assert results[0] == results[1] == results[2]


class TestClassifyDocument:
    def test_classifies_each_page_independently(self):
        # One PDF in the sample set holds two different welders' cards.
        doc = fitz.open()
        for _ in range(2):
            page = doc.new_page(width=528, height=792)
            for nx, ny, text in ID_CARD_LINES:
                page.insert_text((nx * 528, ny * 792), text, fontsize=9)
        extra = doc.new_page(width=528, height=792)
        extra.insert_text((40, 40), "Nothing identifiable here", fontsize=9)
        data = doc.tobytes()
        doc.close()

        results = classify_document(data)

        assert [r.page_number for r in results] == [1, 2, 3]
        assert results[0].canonical_key == "TF-127-R0"
        assert results[1].canonical_key == "TF-127-R0"
        assert results[2].outcome is ClassificationOutcome.TEMPLATE_UNKNOWN

    def test_unopenable_bytes_raise(self):
        # An unopenable file is an infrastructure problem, not a document
        # problem, so unlike every other failure here it raises.
        with pytest.raises(ValueError):
            classify_document(b"this is not a pdf")
