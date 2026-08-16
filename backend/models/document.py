"""Pydantic schemas for parsed source documents.

These describe the output of `engines.pdf_parser` -- the page-attributed text
representation that the LLM extraction layer consumes. They deliberately carry
provenance (page number, extraction method, quality warnings) because every
value Complyx reports must be traceable back to a specific page of a specific
document.
"""

from enum import Enum

from pydantic import BaseModel, Field

# A table is a list of rows; each row is a list of cells; a cell may be empty.
Table = list[list[str | None]]


class ExtractionMethod(str, Enum):
    """How the text for a page (or document) was obtained."""

    NATIVE = "native"
    """Embedded text layer read directly from the PDF."""

    OCR = "ocr"
    """Rasterised and read with Tesseract (scanned or image-only page)."""

    MIXED = "mixed"
    """Document-level only: some pages native, some OCR."""

    NONE = "none"
    """No text could be recovered at all."""


class PageContent(BaseModel):
    """Text and tables recovered from a single PDF page."""

    page_number: int = Field(..., ge=1, description="1-indexed page number.")
    text: str = Field(default="", description="Plain text for this page.")
    tables: list[Table] = Field(
        default_factory=list,
        description="Tables detected on this page, as row/cell matrices.",
    )
    method: ExtractionMethod = ExtractionMethod.NONE
    char_count: int = 0
    estimated_dpi: float | None = Field(
        default=None,
        description=(
            "Effective DPI of the largest raster image on the page. None when "
            "the page carries no raster image (i.e. it is vector/native text)."
        ),
    )


class ParsedDocument(BaseModel):
    """Complete parse result for one uploaded document."""

    filename: str
    document_hash: str = Field(
        ...,
        description="SHA-256 of the raw file bytes. Used for dedup and caching.",
    )
    page_count: int = 0
    pages: list[PageContent] = Field(default_factory=list)
    full_text: str = Field(
        default="",
        description=(
            "Page-delimited concatenation of all page text and rendered tables. "
            "This is the string handed to the extraction prompt."
        ),
    )
    method: ExtractionMethod = ExtractionMethod.NONE
    is_low_quality: bool = Field(
        default=False,
        description=(
            "True when the document is scanned below the legible DPI floor or "
            "yielded too little text to trust. The audit pipeline should route "
            "these to REVIEW_REQUIRED rather than reporting a verdict."
        ),
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Human-readable parse warnings, surfaced to the inspector.",
    )

    @property
    def has_text(self) -> bool:
        """True when any usable text was recovered from any page.

        Deliberately derived from per-page character counts rather than from
        `full_text`: full_text always contains the "=== PAGE n ===" markers, so
        testing it would report a completely blank scan as having content.
        """
        return any(page.char_count > 0 for page in self.pages)
