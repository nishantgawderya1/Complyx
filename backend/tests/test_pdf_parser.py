"""Tests for the PDF parsing engine.

Synthetic PDFs are generated in-process with PyMuPDF so the suite has no
dependency on committed sample documents -- real MTCs are client-confidential
and must never enter the repository.
"""

import fitz
import pytest

from engines.pdf_parser import (
    LOW_DPI_THRESHOLD,
    MIN_NATIVE_CHARS_PER_PAGE,
    PdfParseError,
    _render_table,
    parse_document,
)
from models.document import ExtractionMethod

MTC_PAGE_ONE = """MATERIAL TEST CERTIFICATE
Certificate No: MTC-2026-0412
Specification: ASTM A516/A516M-17
Grade: 70
Heat Number: HT-2891-B
Nominal Thickness: 12 mm
Yield Strength: 265 MPa
Tensile Strength: 480 MPa
Elongation: 28 %
"""

MTC_PAGE_TWO = """CHEMICAL ANALYSIS (Heat Analysis)
C 0.21   Mn 1.35   P 0.012   S 0.008   Si 0.28
Tested in accordance with ASME BPVC Section II Part A.
"""


def _make_pdf(pages: list[str]) -> bytes:
    """Build a native-text PDF containing the given page bodies."""
    doc = fitz.open()
    for body in pages:
        page = doc.new_page()
        page.insert_text((72, 72), body, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


class TestParseDocument:
    def test_extracts_native_text(self):
        parsed = parse_document(_make_pdf([MTC_PAGE_ONE]), "mtc.pdf")

        assert parsed.page_count == 1
        assert parsed.method is ExtractionMethod.NATIVE
        assert parsed.has_text
        assert "265 MPa" in parsed.full_text
        assert "HT-2891-B" in parsed.full_text
        assert parsed.is_low_quality is False
        assert parsed.warnings == []

    def test_tracks_page_numbers_across_multiple_pages(self):
        parsed = parse_document(_make_pdf([MTC_PAGE_ONE, MTC_PAGE_TWO]), "mtc.pdf")

        assert parsed.page_count == 2
        assert [p.page_number for p in parsed.pages] == [1, 2]

        # Page markers are what let the model attribute a value to a page.
        assert "=== PAGE 1 ===" in parsed.full_text
        assert "=== PAGE 2 ===" in parsed.full_text

        # Values must stay on the correct side of the page boundary.
        page_two_start = parsed.full_text.index("=== PAGE 2 ===")
        assert parsed.full_text.index("265 MPa") < page_two_start
        assert parsed.full_text.index("Mn 1.35") > page_two_start

    def test_hash_is_stable_and_content_dependent(self):
        first = _make_pdf([MTC_PAGE_ONE])
        second = _make_pdf([MTC_PAGE_TWO])

        assert (
            parse_document(first, "a.pdf").document_hash
            == parse_document(first, "b.pdf").document_hash
        )
        assert (
            parse_document(first, "a.pdf").document_hash
            != parse_document(second, "a.pdf").document_hash
        )

    def test_blank_document_is_flagged_not_silently_empty(self):
        """A document yielding no text must warn, never return a clean empty parse.

        This is the failure mode that leads to a confident wrong verdict: no
        text extracted, no values found, nothing to compare, and a downstream
        layer treating the absence as 'nothing failed'.
        """
        doc = fitz.open()
        doc.new_page()
        data = doc.tobytes()
        doc.close()

        parsed = parse_document(data, "blank.pdf")

        assert parsed.has_text is False
        assert parsed.is_low_quality is True
        assert parsed.warnings

    def test_rejects_non_pdf_bytes(self):
        with pytest.raises(PdfParseError):
            parse_document(b"this is not a pdf", "invoice.txt")

    def test_page_char_count_reflects_stripped_text(self):
        parsed = parse_document(_make_pdf([MTC_PAGE_ONE]), "mtc.pdf")
        page = parsed.pages[0]

        assert page.char_count == len(page.text.strip())
        assert page.char_count > MIN_NATIVE_CHARS_PER_PAGE


class TestRenderTable:
    def test_renders_rows_pipe_delimited(self):
        table = [["Property", "Value", "Unit"], ["Yield", "265", "MPa"]]

        assert _render_table(table) == "Property | Value | Unit\nYield | 265 | MPa"

    def test_drops_fully_empty_rows_and_normalises_cells(self):
        table = [["Yield", None, "MPa"], [None, None, None], ["Tensile", "480\n", "MPa"]]

        assert _render_table(table) == "Yield |  | MPa\nTensile | 480 | MPa"


def test_low_dpi_threshold_is_sane():
    """Guard the constant: below ~150 DPI, digit strokes are unreliable."""
    assert LOW_DPI_THRESHOLD >= 150
