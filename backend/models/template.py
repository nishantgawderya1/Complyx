"""Pydantic schemas for form templates and classification.

These describe the *shape* of a known NPCIL/Tata form: where its format number
is printed, and where each field's value sits on the page.

The premise, from `docs/architecture.md`: these are numbered forms, not
free-form documents. The same six templates repeat across every welder package
on the site. So we classify the form, look up its template, and read only the
known field regions -- rather than doing general document understanding.

Two things measured on the real sample packages shaped this module, and both
are worth stating because they contradict the obvious design:

**1. Regions cannot be fixed rectangles.**
Two scans of the *same* form drift by up to 3.6% of page height, and the drift
grows down the page -- it is a scale-and-offset difference, not a translation.
On the WPQR the footer moves 9.6% of page height between pages 1 and 2. A
hard-coded normalised rectangle tight enough to isolate a value would miss it
on the next scan. So a region is defined **relative to an anchor**: a stable
piece of printed form furniture ("WELDER NAME", "Actual Values") located by
text match, with the value box expressed as an offset from it. The anchor
drifts with the scan and the region drifts with the anchor.

**2. The two-column WPQR needs two anchors, not one.**
`ACTUAL VALUES` and `QUALIFIED RANGE` are separate columns of the same row, and
the flat text layer interleaves them beyond recovery. Taking the *x* bounds
from the column-header anchor and the *y* bounds from the row-label anchor
reconstructs the cell by intersection, which is the association the text stream
destroys. This is why `RegionSpec` carries an x-anchor and a y-anchor
independently.

`rect` remains mandatory on every region: it is the declared fallback when an
anchor cannot be found, and the clamp that stops a mis-resolved anchor pointing
off the page. Falling back is never silent -- it downgrades confidence and
records a warning, per the "never guess quietly" rule in CLAUDE.md section 5.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class FormType(str, Enum):
    """The six document types that make up one qualification package.

    Mirrors `SourceDocument.doc_type` in `docs/data-model.md`.
    """

    REQUISITION = "requisition"
    WELD_DATA_RECORD = "weld_data_record"
    SAMPLE_CARD = "sample_card"
    LAB_REPORT = "lab_report"
    WPQR = "wpqr"
    ID_CARD = "id_card"


class ReadMethod(str, Enum):
    """How a field's value was obtained. Stored on every extracted field."""

    TEMPLATE_REGION = "template_region"
    """Read from a template-defined region located by its anchor."""

    TEMPLATE_REGION_FALLBACK = "template_region_fallback"
    """Anchor not found; read from the template's declared fallback rect.

    Distinct from TEMPLATE_REGION because the value is materially less
    trustworthy and a reviewer must be able to filter on it.
    """

    FULL_PAGE = "full_page"
    """Whole-page extraction, used when no template matched."""

    CHECKBOX_CV = "checkbox_cv"
    CHECKBOX_VISION = "checkbox_vision"
    CHECKBOX_AGREED = "checkbox_agreed"
    """Both checkbox readers agreed. Disagreement never produces a value."""


class ValueKind(str, Enum):
    """What kind of value a region is expected to hold.

    Drives downstream parsing and, for CHECKBOX, forces the dual-read path in
    `engines/checkbox_detector.py` (build step 2) rather than a text read.
    """

    TEXT = "text"
    DATE = "date"
    CHECKBOX = "checkbox"


class XMode(str, Enum):
    """How a region's horizontal bounds derive from its x-anchor."""

    RIGHT_OF = "right_of"
    """Value sits to the right of the anchor: a "LABEL: value" row."""

    ALIGN = "align"
    """Value shares the anchor's x span: a column header over its cells."""


class YMode(str, Enum):
    """How a region's vertical bounds derive from its y-anchor."""

    SAME_ROW = "same_row"
    """Value is on the anchor's own baseline."""

    BELOW = "below"
    """Value sits under the anchor: a column header, or a table row label."""


class BBox(BaseModel):
    """A rectangle in normalised page coordinates.

    Normalised (0..1 fractions of page width and height) rather than PDF
    points, because the same form scans to different page sizes -- the welder
    identity card arrives as both 528x792 and 542x792 points. A point-based
    region would be wrong on one of them.

    Origin is top-left, matching PyMuPDF's page coordinate space.
    """

    x0: float = Field(..., ge=0.0, le=1.0)
    y0: float = Field(..., ge=0.0, le=1.0)
    x1: float = Field(..., ge=0.0, le=1.0)
    y1: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_ordering(self) -> BBox:
        if self.x1 <= self.x0:
            raise ValueError(f"x1 ({self.x1}) must exceed x0 ({self.x0})")
        if self.y1 <= self.y0:
            raise ValueError(f"y1 ({self.y1}) must exceed y0 ({self.y0})")
        return self

    def to_absolute(self, page_width: float, page_height: float) -> tuple[float, float, float, float]:
        """Return this box in PDF points for a page of the given size."""
        return (
            self.x0 * page_width,
            self.y0 * page_height,
            self.x1 * page_width,
            self.y1 * page_height,
        )

    def clamp(self, bounds: BBox) -> BBox:
        """Return this box confined to `bounds`.

        Used to stop a mis-resolved anchor producing a region that runs off the
        page or swallows a neighbouring column.
        """
        x0 = min(max(self.x0, bounds.x0), bounds.x1)
        x1 = min(max(self.x1, bounds.x0), bounds.x1)
        y0 = min(max(self.y0, bounds.y0), bounds.y1)
        y1 = min(max(self.y1, bounds.y0), bounds.y1)

        # A fully-clipped box would violate the ordering validator. Collapsing
        # to the bounds is the honest answer: the caller sees a region the size
        # of its own clamp and the low confidence that comes with a fallback.
        if x1 <= x0 or y1 <= y0:
            return bounds.model_copy()
        return BBox(x0=x0, y0=y0, x1=x1, y1=y1)


class AnchorSpec(BaseModel):
    """Printed form furniture used to locate a region.

    An anchor is text that belongs to the blank form, not to the filled-in
    values -- a field label, a column heading, a section title. It is therefore
    present on every instance of the form and moves with the scan.

    `text` is matched against the page's normalised text, so it tolerates the
    whitespace and case noise in an OCR text layer but not character
    substitution. Where OCR reliably mangles a label, list the mangled reading
    in `alternates` explicitly. That keeps the match table auditable -- the same
    discipline `knowledge_base/standards_loader.py` applies to grade aliases,
    and for the same reason: a similarity score can silently pick the wrong row.
    """

    text: str = Field(..., min_length=1, description="Expected anchor text.")
    alternates: list[str] = Field(
        default_factory=list,
        description="Known OCR readings of the same anchor, matched exactly.",
    )
    occurrence: int = Field(
        default=0,
        ge=0,
        description=(
            "Which match to use when the anchor text appears more than once. "
            "The identity card prints 'Format No.' twice (front and back "
            "face), so the ordinal is load-bearing, not a tiebreak."
        ),
    )
    search_band: BBox | None = Field(
        default=None,
        description=(
            "Restrict the search to this part of the page. Narrows an anchor "
            "that would otherwise be ambiguous."
        ),
    )


class RegionSpec(BaseModel):
    """Where a field's value sits, relative to its anchors.

    At least one of `rect` (always) and the anchors (optionally) is used:
    anchors when they resolve, `rect` when they do not.
    """

    rect: BBox = Field(
        ...,
        description=(
            "Fallback region, and the clamp applied to any anchor-derived "
            "region. Mandatory: a region with no declared bounds cannot be "
            "sanity-checked."
        ),
    )
    x_anchor: AnchorSpec | None = None
    x_mode: XMode = XMode.RIGHT_OF
    x_width: float | None = Field(
        default=None,
        gt=0.0,
        le=1.0,
        description="Normalised width when the x bounds derive from an anchor.",
    )
    x_offset: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description=(
            "Normalised gap between the anchor and the start of the region. "
            "Needed where a value does not butt up against its label -- the "
            "WPQR's 'No' checkbox sits past the 'Yes' box, not against the "
            "row label. Expressed as an offset rather than a second anchor so "
            "it drifts with the scan along with everything else."
        ),
    )
    y_anchor: AnchorSpec | None = None
    y_mode: YMode = YMode.SAME_ROW
    y_height: float | None = Field(
        default=None,
        gt=0.0,
        le=1.0,
        description="Normalised height when the y bounds derive from an anchor.",
    )
    y_offset: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Normalised gap between the anchor and the region, vertically.",
    )
    pad: float = Field(
        default=0.002,
        ge=0.0,
        le=0.1,
        description=(
            "Normalised slack added around a resolved region. Kept small: "
            "body lines on these forms start about 0.03 of page height apart "
            "and stand about 0.024 tall, so a region padded much beyond 0.002 "
            "reaches the centre of the next line and swallows it."
        ),
    )

    @model_validator(mode="after")
    def _check_anchor_dimensions(self) -> RegionSpec:
        if self.x_anchor is not None and self.x_width is None:
            raise ValueError("x_anchor requires x_width")
        if self.y_anchor is not None and self.y_height is None:
            raise ValueError("y_anchor requires y_height")
        return self


class FieldSpec(BaseModel):
    """One readable field on a form."""

    name: str = Field(..., min_length=1)
    region: RegionSpec
    value_kind: ValueKind = ValueKind.TEXT
    description: str = ""
    required: bool = Field(
        default=True,
        description=(
            "A required field that cannot be read routes the document to "
            "REVIEW. It never reports 'no finding'."
        ),
    )


class CheckboxSpec(BaseModel):
    """A Yes/No checkbox pair read by two independent methods.

    The '3 layers minimum' box on the WPQR decides between 'max. to be welded'
    and a 2t thickness limit -- the single most consequential mark on the form,
    and not text. `engines/checkbox_detector.py` (build step 2) reads each box
    with OpenCV ink density and with a vision model. Agreement gives
    CHECKBOX_AGREED; **disagreement is never resolved automatically** and
    routes to REVIEW.
    """

    name: str = Field(..., min_length=1)
    yes_region: RegionSpec
    no_region: RegionSpec
    clause_ref: str = ""
    description: str = ""


class FormTemplate(BaseModel):
    """The field map for one revision of one numbered form.

    Keyed by `canonical_key`, which is the canonicalised format number -- see
    `knowledge_base/template_registry.py` for how a scanned, OCR-mangled format
    number is reduced to it.
    """

    canonical_key: str = Field(..., min_length=1, description='e.g. "TF-127-R0".')
    form_type: FormType
    format_no: str = Field(..., description='As printed, e.g. "NPCIL/QMD/TF-127".')
    format_rev: str = Field(..., description='As printed, e.g. "R0".')
    title: str = ""
    template_version: str = Field(
        ...,
        description=(
            "Stamped on every value read through this template. A region "
            "moves -> this changes, so a stored finding stays traceable to the "
            "geometry that produced it."
        ),
    )
    landscape: bool = Field(
        default=False,
        description="True when the blank form is wider than it is tall.",
    )
    signature_tokens: list[str] = Field(
        default_factory=list,
        description=(
            "Canonicalised tokens that corroborate a classification, checked "
            "after the format number resolves. Evidence, never the decision."
        ),
    )
    fields: list[FieldSpec] = Field(default_factory=list)
    checkboxes: list[CheckboxSpec] = Field(default_factory=list)
    verified: bool = Field(
        default=False,
        description=(
            "False until a qualified reviewer confirms the regions against a "
            "real form. Unverified templates are usable in development and "
            "must be visibly flagged in any output."
        ),
    )
    verified_by: str | None = None
    verified_date: str | None = None
    source: str = ""
    notes: str = ""

    @model_validator(mode="after")
    def _check_unique_names(self) -> FormTemplate:
        names = [f.name for f in self.fields] + [c.name for c in self.checkboxes]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(
                f"{self.canonical_key}: duplicate field names {sorted(duplicates)}"
            )
        return self


class ClassificationOutcome(str, Enum):
    """Result of trying to identify which form a page is."""

    MATCHED = "matched"
    """One template matched. Region extraction may proceed."""

    TEMPLATE_UNKNOWN = "template_unknown"
    """No format number resolved to a known template.

    The caller falls back to whole-page extraction and flags the document, so a
    human knows which path produced the values. Never a silent guess.
    """

    AMBIGUOUS = "ambiguous"
    """The page resolved to more than one template.

    Treated as a failure, not a tiebreak. Picking one would be exactly the
    confident-wrong-answer failure mode the architecture exists to avoid.
    """


class ClassificationResult(BaseModel):
    """What the form classifier concluded about one page."""

    page_number: int = Field(..., ge=1)
    outcome: ClassificationOutcome
    canonical_key: str | None = None
    form_type: FormType | None = None
    template_version: str | None = None
    raw_format_text: str | None = Field(
        default=None,
        description="The format-number text as it was found on the page.",
    )
    canonical_candidates: list[str] = Field(
        default_factory=list,
        description="Every key the page's format numbers resolved to.",
    )
    found_in_band: str | None = Field(
        default=None,
        description='Which band the format number was found in: header/footer/page.',
    )
    bbox: BBox | None = Field(
        default=None,
        description="Where the format number sits, for UI highlighting.",
    )
    matched_signature_tokens: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = Field(
        default="",
        description="Why the outcome is what it is. Shown to the inspector.",
    )
    template_verified: bool = Field(
        default=False,
        description="Mirrors FormTemplate.verified, so output can flag it.",
    )

    @property
    def matched(self) -> bool:
        return self.outcome is ClassificationOutcome.MATCHED


class ExtractedField(BaseModel):
    """One value read from a template region, with its provenance.

    Mirrors `ExtractedField` in `docs/data-model.md`. `bbox` is the region the
    value came from, so the UI can highlight the exact box behind a finding.
    """

    name: str
    value: str | None = None
    unit: str | None = None
    page: int = Field(..., ge=1)
    bbox: BBox | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    read_method: ReadMethod = ReadMethod.TEMPLATE_REGION
    source_snippet: str = ""
    value_kind: ValueKind = ValueKind.TEXT
    needs_review: bool = Field(
        default=False,
        description="True when this value must not be used without a human look.",
    )
    review_reason: str = ""
    template_version: str | None = None

    @property
    def is_empty(self) -> bool:
        return not (self.value or "").strip()


class TemplateExtraction(BaseModel):
    """Everything read from one page through one template.

    Carries `template_version` and `template_verified` alongside the values,
    because a value is only as trustworthy as the geometry that found it and an
    unverified template must stay visibly unverified all the way to the UI.
    """

    page_number: int = Field(..., ge=1)
    canonical_key: str
    template_version: str
    template_verified: bool = False
    fields: list[ExtractedField] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        """True when any field on this page requires a human look.

        A page with an unreadable required field is never a clean result, so
        callers gate on this rather than on the presence of values.
        """
        return any(f.needs_review for f in self.fields)

    def by_name(self, name: str) -> ExtractedField | None:
        """Look up one field, or None when the template does not define it."""
        return next((f for f in self.fields if f.name == name), None)
