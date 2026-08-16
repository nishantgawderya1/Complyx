"""PDF parsing engine.

Turns an uploaded engineering document (primarily a Material Test Certificate)
into a single page-attributed text representation for the extraction layer.

Strategy, applied per page:

1. **Native text** via PyMuPDF. Fast and exact on machine-generated PDFs, which
   is the majority of supplier-issued MTCs.
2. **Tables** via pdfplumber. MTC values almost always live in tables, and a
   flat text dump loses the row/column association between a property name and
   its value. Tables are rendered back into the text stream in a delimited form
   the LLM can follow.
3. **Tesseract OCR fallback** when a page yields no meaningful native text --
   scanned certificates, photocopies, stamped paper forms.

Design rule: this module does not raise on recoverable problems. A page that
fails to OCR, a missing Tesseract binary, or a low-DPI scan all produce a
*warning* on the returned `ParsedDocument`. The audit pipeline reads those
warnings and routes the job to REVIEW_REQUIRED. Silently returning partial text
as if it were complete is the one failure mode this engine must never have,
because it is the path to a confident wrong PASS.
"""

from __future__ import annotations

import hashlib
import io
import logging

import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image

from config import settings
from models.document import (
    ExtractionMethod,
    PageContent,
    ParsedDocument,
    Table,
)

logger = logging.getLogger(__name__)

# A page with fewer than this many characters of native text is treated as a
# scanned image and sent to OCR. Real MTC pages carry hundreds of characters;
# a scanned page typically yields 0-20 characters of stray text-layer noise.
MIN_NATIVE_CHARS_PER_PAGE = 50

# Resolution used when rasterising a page for OCR. 300 DPI is the accuracy
# sweet spot for Tesseract on printed engineering forms.
OCR_RENDER_DPI = 300

# Scans below this effective DPI lose digit strokes -- a 6 becomes an 8, a 3
# becomes an 8. Any document at or under this floor is flagged low quality.
LOW_DPI_THRESHOLD = 150

# Guard against a mis-uploaded 500-page package being pushed through OCR.
MAX_PAGES = 50


class PdfParseError(Exception):
    """Raised when a file cannot be opened as a PDF at all."""


def _configure_tesseract() -> None:
    """Point pytesseract at an explicit binary if one is configured."""
    if settings.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


def _tesseract_available() -> bool:
    """Return True when a usable Tesseract binary is reachable."""
    _configure_tesseract()
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # pragma: no cover - environment dependent
        return False


def _estimate_page_dpi(page: fitz.Page) -> float | None:
    """Estimate the effective DPI of the largest raster image on a page.

    Returns None when the page has no raster images, which means it is native
    vector/text content and the notion of scan DPI does not apply.
    """
    try:
        images = page.get_image_info()
    except Exception:  # pragma: no cover - malformed page objects
        return None

    best_dpi: float | None = None
    best_area = 0.0

    for info in images:
        pixel_width = float(info.get("width") or 0)
        bbox = info.get("bbox")
        if not pixel_width or not bbox:
            continue

        # bbox is in PDF points (72 points to the inch).
        displayed_width_pt = float(bbox[2]) - float(bbox[0])
        displayed_height_pt = float(bbox[3]) - float(bbox[1])
        if displayed_width_pt <= 0:
            continue

        area = displayed_width_pt * displayed_height_pt
        if area <= best_area:
            continue

        best_area = area
        best_dpi = pixel_width / (displayed_width_pt / 72.0)

    return best_dpi


def _ocr_page(page: fitz.Page) -> str:
    """Rasterise a page at OCR_RENDER_DPI and read it with Tesseract."""
    zoom = OCR_RENDER_DPI / 72.0
    pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    return pytesseract.image_to_string(image)


def _extract_tables(pdf_bytes: bytes) -> dict[int, list[Table]]:
    """Extract tables for every page, keyed by 1-indexed page number.

    pdfplumber is opened once for the whole document rather than per page --
    reopening per page on a 20-page scan is measurably slower.
    """
    tables_by_page: dict[int, list[Table]] = {}

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for index, page in enumerate(pdf.pages[:MAX_PAGES], start=1):
                try:
                    found = page.extract_tables()
                except Exception as exc:  # pragma: no cover - parser quirks
                    logger.warning("Table extraction failed on page %s: %s", index, exc)
                    continue
                if found:
                    tables_by_page[index] = found
    except Exception as exc:  # pragma: no cover - pdfplumber open failure
        logger.warning("pdfplumber could not open document: %s", exc)

    return tables_by_page


def _render_table(table: Table) -> str:
    """Render a table as pipe-delimited rows for inclusion in the text stream."""
    lines: list[str] = []
    for row in table:
        cells = [(cell or "").replace("\n", " ").strip() for cell in row]
        if not any(cells):
            continue
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def _build_full_text(pages: list[PageContent]) -> str:
    """Concatenate page text and tables with explicit page markers.

    Page markers are load-bearing: the extraction prompt asks the model to
    report which page each value came from, and `extracted_values.page_number`
    stores it for the audit trail.
    """
    blocks: list[str] = []

    for page in pages:
        block = [f"=== PAGE {page.page_number} ==="]

        if page.text.strip():
            block.append(page.text.strip())

        for table_index, table in enumerate(page.tables, start=1):
            rendered = _render_table(table)
            if rendered:
                block.append(f"[TABLE {table_index}]\n{rendered}")

        blocks.append("\n\n".join(block))

    return "\n\n".join(blocks)


def parse_document(file_bytes: bytes, filename: str) -> ParsedDocument:
    """Parse an uploaded PDF into page-attributed text and tables.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename: Original filename, retained for the audit record.

    Returns:
        A `ParsedDocument` carrying per-page text, tables, extraction method,
        quality warnings and the SHA-256 hash of the source bytes.

    Raises:
        PdfParseError: The bytes could not be opened as a PDF.
    """
    document_hash = hashlib.sha256(file_bytes).hexdigest()
    warnings: list[str] = []

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise PdfParseError(f"Could not open '{filename}' as a PDF: {exc}") from exc

    parsed = ParsedDocument(filename=filename, document_hash=document_hash)

    try:
        if doc.is_encrypted and not doc.authenticate(""):
            raise PdfParseError(
                f"'{filename}' is password protected and cannot be parsed."
            )

        total_pages = doc.page_count
        parsed.page_count = total_pages

        if total_pages == 0:
            parsed.warnings.append("Document contains no pages.")
            parsed.is_low_quality = True
            return parsed

        if total_pages > MAX_PAGES:
            warnings.append(
                f"Document has {total_pages} pages; only the first {MAX_PAGES} "
                "were parsed."
            )

        tables_by_page = _extract_tables(file_bytes)
        ocr_checked = False
        ocr_usable = False
        methods_used: set[ExtractionMethod] = set()

        for page_index in range(min(total_pages, MAX_PAGES)):
            page = doc.load_page(page_index)
            page_number = page_index + 1

            try:
                text = page.get_text("text") or ""
            except Exception as exc:  # pragma: no cover - malformed page
                logger.warning("Native text failed on page %s: %s", page_number, exc)
                text = ""

            method = ExtractionMethod.NATIVE if text.strip() else ExtractionMethod.NONE
            estimated_dpi = _estimate_page_dpi(page)

            # Scanned page: too little native text to be a real certificate page.
            if len(text.strip()) < MIN_NATIVE_CHARS_PER_PAGE:
                if not ocr_checked:
                    ocr_checked = True
                    ocr_usable = _tesseract_available()
                    if not ocr_usable:
                        warnings.append(
                            "Document appears scanned but Tesseract OCR is not "
                            "available; text could not be recovered."
                        )

                if ocr_usable:
                    try:
                        ocr_text = _ocr_page(page)
                    except Exception as exc:
                        logger.warning("OCR failed on page %s: %s", page_number, exc)
                        warnings.append(f"OCR failed on page {page_number}.")
                        ocr_text = ""

                    if ocr_text.strip():
                        text = ocr_text
                        method = ExtractionMethod.OCR

                if estimated_dpi is not None and estimated_dpi < LOW_DPI_THRESHOLD:
                    warnings.append(
                        f"Page {page_number} is scanned at approximately "
                        f"{estimated_dpi:.0f} DPI, below the {LOW_DPI_THRESHOLD} "
                        "DPI floor for reliable digit recognition."
                    )
                    parsed.is_low_quality = True

            if method is not ExtractionMethod.NONE:
                methods_used.add(method)

            parsed.pages.append(
                PageContent(
                    page_number=page_number,
                    text=text,
                    tables=tables_by_page.get(page_number, []),
                    method=method,
                    char_count=len(text.strip()),
                    estimated_dpi=estimated_dpi,
                )
            )
    finally:
        doc.close()

    parsed.full_text = _build_full_text(parsed.pages)

    if not methods_used:
        parsed.method = ExtractionMethod.NONE
    elif len(methods_used) > 1:
        parsed.method = ExtractionMethod.MIXED
    else:
        parsed.method = methods_used.pop()

    if not parsed.has_text:
        warnings.append("No text could be recovered from this document.")
        parsed.is_low_quality = True

    empty_pages = [p.page_number for p in parsed.pages if p.char_count == 0]
    if empty_pages and len(empty_pages) < len(parsed.pages):
        warnings.append(
            "No text recovered from page(s): "
            + ", ".join(str(n) for n in empty_pages)
            + "."
        )

    parsed.warnings.extend(warnings)
    return parsed
