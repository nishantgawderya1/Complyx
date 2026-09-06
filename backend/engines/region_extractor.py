"""Region extraction: read the fields a matched template defines.

Given a page and the template the classifier matched, resolve each field's
region and read what sits inside it.

## What this module is, and what it is not

It resolves **geometry** and reads whatever text layer the page already has.
That is enough to prove the template registry on the sample packages, and it
is what the reconciliation engine (build step 4) needs.

It is not the final read path. Per `docs/architecture.md` the values that back
a verdict come from a vision model reading the cropped region -- text-only OCR
cannot preserve the Actual Values / Qualified Range column association and
degrades badly on stamped and signed scans. `region_pixmap` here is the crop
that path will take: the regions this module resolves are exactly the regions
the vision model will be handed, so the geometry is shared and only the reader
changes.

## Confidence is about provenance, not about the characters

A value read from a region whose anchors both resolved is trustworthy in a way
one read from a fallback rectangle is not, and the score says so. It is not a
guess at OCR accuracy -- nothing here can measure that. It says how firmly the
region was located.

## Checkboxes are never read here

A checkbox region is resolved and returned, but no value is read from it. The
text layer of the sample WPQR does render the tick as a stray "v", and reading
that would be a third, unsanctioned method -- a stray mark reads as a tick, and
a tick the OCR dropped reads as unchecked, both silently. The architecture
requires two independent reads (OpenCV ink density and a vision model) with any
disagreement routed to REVIEW. Until `engines/checkbox_detector.py` exists
(build step 2), checkbox fields come back with no value and `needs_review` set.
"""

from __future__ import annotations

import logging

import fitz

from engines.page_geometry import (
    PageWord,
    extract_words,
    resolve_anchor,
    union_bbox,
    words_in_band,
)
from models.template import (
    BBox,
    CheckboxSpec,
    ExtractedField,
    FieldSpec,
    FormTemplate,
    ReadMethod,
    RegionSpec,
    TemplateExtraction,
    ValueKind,
    XMode,
    YMode,
)

logger = logging.getLogger(__name__)

# Confidence by how firmly the region was located. Both anchors resolving means
# the region tracked the scan's own drift; a fallback rect means it did not.
CONFIDENCE_BOTH_ANCHORS = 0.90
CONFIDENCE_ONE_ANCHOR = 0.60
CONFIDENCE_NO_ANCHOR = 0.40

# Resolution for region crops handed to the vision model. 300 DPI is the
# accuracy floor for printed engineering forms, matching OCR_RENDER_DPI in
# engines/pdf_parser.py.
REGION_RENDER_DPI = 300


def _clean_value(raw: str) -> str | None:
    """Tidy a value read from a region, or return None when it is empty.

    Strips the label punctuation that leaks in when a region starts just after
    a colon -- the identity card's name cell reads ": RAJ NARAYAN PRASAD" -- and
    collapses the whitespace introduced by joining separately-boxed words.

    Only leading and trailing separators are removed. Nothing inside the value
    is touched: correcting characters is the extraction layer's job to *report*,
    never to silently perform.
    """
    collapsed = " ".join(raw.split())
    trimmed = collapsed.strip(" :|.,;-")
    return trimmed or None


def _resolve_axis_x(
    words: list[PageWord], spec: RegionSpec
) -> tuple[float, float, bool]:
    """Resolve horizontal bounds. Returns (x0, x1, used_anchor)."""
    if spec.x_anchor is None:
        return spec.rect.x0, spec.rect.x1, False

    anchor = resolve_anchor(
        words,
        spec.x_anchor.text,
        spec.x_anchor.alternates,
        spec.x_anchor.occurrence,
        spec.x_anchor.search_band,
    )
    if anchor is None:
        return spec.rect.x0, spec.rect.x1, False

    origin = anchor.bbox.x1 if spec.x_mode is XMode.RIGHT_OF else anchor.bbox.x0
    x0 = origin + spec.x_offset
    return x0, x0 + (spec.x_width or 0.0), True


def _resolve_axis_y(
    words: list[PageWord], spec: RegionSpec
) -> tuple[float, float, bool]:
    """Resolve vertical bounds. Returns (y0, y1, used_anchor)."""
    if spec.y_anchor is None:
        return spec.rect.y0, spec.rect.y1, False

    anchor = resolve_anchor(
        words,
        spec.y_anchor.text,
        spec.y_anchor.alternates,
        spec.y_anchor.occurrence,
        spec.y_anchor.search_band,
    )
    if anchor is None:
        return spec.rect.y0, spec.rect.y1, False

    origin = anchor.bbox.y1 if spec.y_mode is YMode.BELOW else anchor.bbox.y0
    y0 = origin + spec.y_offset
    return y0, y0 + (spec.y_height or 0.0), True


def resolve_region(
    words: list[PageWord], spec: RegionSpec
) -> tuple[BBox, int, list[str]]:
    """Locate a region on the page.

    Returns the resolved box, how many of its anchors resolved (0, 1 or 2), and
    any warnings. An anchor that cannot be found is never fatal: the axis falls
    back to the declared rect, the anchor count drops, and a warning records it
    so the value carries TEMPLATE_REGION_FALLBACK rather than passing itself
    off as an anchored read.
    """
    warnings: list[str] = []

    x0, x1, x_anchored = _resolve_axis_x(words, spec)
    y0, y1, y_anchored = _resolve_axis_y(words, spec)

    if spec.x_anchor is not None and not x_anchored:
        warnings.append(f"x-anchor '{spec.x_anchor.text}' not found; used fallback rect")
    if spec.y_anchor is not None and not y_anchored:
        warnings.append(f"y-anchor '{spec.y_anchor.text}' not found; used fallback rect")

    box = BBox(
        x0=min(max(x0 - spec.pad, 0.0), 1.0),
        y0=min(max(y0 - spec.pad, 0.0), 1.0),
        x1=min(max(x1 + spec.pad, 0.0), 1.0),
        y1=min(max(y1 + spec.pad, 0.0), 1.0),
    )

    anchors_used = int(x_anchored) + int(y_anchored)
    # An anchor that resolves to the wrong place can push the region off the
    # page. Clamping to the full page keeps the box valid; the low anchor count
    # and the warnings are what tell the reviewer it may be wrong.
    return box.clamp(BBox(x0=0.0, y0=0.0, x1=1.0, y1=1.0)), anchors_used, warnings


def _confidence_for(anchors_used: int, anchors_declared: int) -> float:
    """Score a region by how firmly it was located."""
    if anchors_declared == 0:
        return CONFIDENCE_NO_ANCHOR
    if anchors_used >= 2:
        return CONFIDENCE_BOTH_ANCHORS
    if anchors_used == 1:
        return CONFIDENCE_ONE_ANCHOR if anchors_declared > 1 else CONFIDENCE_BOTH_ANCHORS
    return CONFIDENCE_NO_ANCHOR


def extract_field(
    words: list[PageWord],
    spec: FieldSpec,
    page_number: int,
    template_version: str,
) -> ExtractedField:
    """Read one template field from the page's text layer."""
    region, anchors_used, warnings = resolve_region(words, spec.region)
    declared = int(spec.region.x_anchor is not None) + int(spec.region.y_anchor is not None)

    if spec.value_kind is ValueKind.CHECKBOX:  # pragma: no cover - routed earlier
        raise ValueError(f"{spec.name}: checkbox fields go through extract_checkbox")

    contained = words_in_band(words, region)

    # An anchored region that resolves empty is usually a merged OCR token:
    # page 2 of the sample identity card reads the label and its value as the
    # single word "NO.:TPL/GHAVPW-71", so the anchor's box swallows the value
    # and `right_of` starts past it. Retrying against the template's declared
    # rect recovers the value from bounds that were written down in advance.
    #
    # This is a widening, not a guess: the rect is part of the template, the
    # retry is unconditional and deterministic, and the result is demoted to
    # TEMPLATE_REGION_FALLBACK and flagged for review rather than passing
    # itself off as an anchored read.
    recovered_from_rect = False
    if not contained and anchors_used > 0:
        rect_words = words_in_band(words, spec.region.rect)
        if rect_words:
            contained = rect_words
            region = spec.region.rect
            recovered_from_rect = True
            warnings.append(
                "anchored region resolved empty (likely a merged OCR token); "
                "recovered from the template's fallback rect"
            )

    value = _clean_value(" ".join(w.text for w in contained))

    confidence = _confidence_for(anchors_used, declared)
    read_method = ReadMethod.TEMPLATE_REGION
    if anchors_used != declared or recovered_from_rect:
        read_method = ReadMethod.TEMPLATE_REGION_FALLBACK
    if recovered_from_rect:
        confidence = CONFIDENCE_NO_ANCHOR

    needs_review = False
    review_reason = ""

    if value is None:
        confidence = 0.0
        if spec.required:
            needs_review = True
            review_reason = (
                f"Required field '{spec.name}' is empty in its resolved region. "
                "A field that cannot be read routes to REVIEW, never to 'no finding'."
            )
    elif warnings:
        needs_review = True
        review_reason = "; ".join(warnings)

    return ExtractedField(
        name=spec.name,
        value=value,
        page=page_number,
        # The tight box around the words actually found is better provenance
        # than the search region: it is what the UI should highlight. The
        # search region is what gets reported when nothing was found.
        bbox=union_bbox(contained) or region,
        confidence=confidence,
        read_method=read_method,
        source_snippet=value or "",
        value_kind=spec.value_kind,
        needs_review=needs_review,
        review_reason=review_reason,
        template_version=template_version,
    )


def extract_checkbox(
    words: list[PageWord],
    spec: CheckboxSpec,
    page_number: int,
    template_version: str,
) -> ExtractedField:
    """Resolve a checkbox's regions without reading a value from them.

    Returns the Yes-box region as the field's bbox so the geometry is
    inspectable, and sets `needs_review` unconditionally: the dual-read
    detector that decides checked or unchecked is build step 2, and no other
    method is permitted to stand in for it.
    """
    yes_region, yes_anchors, yes_warnings = resolve_region(words, spec.yes_region)
    _, no_anchors, no_warnings = resolve_region(words, spec.no_region)

    unresolved = yes_warnings + no_warnings
    reason = (
        f"Checkbox '{spec.name}' requires the dual OpenCV/vision read "
        f"(engines/checkbox_detector.py, build step 2). No value is inferred "
        f"from the text layer."
    )
    if unresolved:
        reason += " Region resolution was degraded: " + "; ".join(unresolved)

    return ExtractedField(
        name=spec.name,
        value=None,
        page=page_number,
        bbox=yes_region,
        confidence=0.0,
        read_method=ReadMethod.CHECKBOX_AGREED,
        value_kind=ValueKind.CHECKBOX,
        needs_review=True,
        review_reason=reason,
        template_version=template_version,
        source_snippet="",
    )


def extract_page(
    page: fitz.Page,
    template: FormTemplate,
    page_number: int,
) -> TemplateExtraction:
    """Read every field and checkbox `template` defines from `page`."""
    words = extract_words(page)

    result = TemplateExtraction(
        page_number=page_number,
        canonical_key=template.canonical_key,
        template_version=template.template_version,
        template_verified=template.verified,
    )

    if not words:
        result.warnings.append(
            "No text layer on this page; no region could be read. The page "
            "must be rasterised and read by the vision model."
        )
        return result

    for spec in template.fields:
        result.fields.append(
            extract_field(words, spec, page_number, template.template_version)
        )

    for checkbox in template.checkboxes:
        result.fields.append(
            extract_checkbox(words, checkbox, page_number, template.template_version)
        )

    if not template.verified:
        result.warnings.append(
            f"Template {template.template_version} is UNVERIFIED. Every value "
            "here must be flagged as such wherever it is shown."
        )

    missing = [f.name for f in result.fields if f.needs_review]
    if missing:
        result.warnings.append(
            f"{len(missing)} field(s) need review: {', '.join(missing)}"
        )

    return result


def region_pixmap(
    page: fitz.Page,
    region: BBox,
    dpi: int = REGION_RENDER_DPI,
) -> fitz.Pixmap:
    """Rasterise one region of a page.

    This is the crop the vision model reads, and the crop OpenCV measures ink
    density in for a checkbox. Kept here so the region geometry has exactly one
    definition: whatever reads the region gets the same pixels.
    """
    rect = page.rect
    x0, y0, x1, y1 = region.to_absolute(float(rect.width), float(rect.height))
    zoom = dpi / 72.0
    return page.get_pixmap(
        matrix=fitz.Matrix(zoom, zoom),
        clip=fitz.Rect(x0, y0, x1, y1),
    )
