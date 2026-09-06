"""Form classifier: decide which numbered form a page is.

This is build step 1 and the foundation for everything after it. Nothing can be
read from a known region until we know which form the page is.

## How it decides

    page words (normalised, spatially sorted)
      -> scan bands in priority order: header, footer, whole page
      -> canonicalise every format number found       (template_registry)
      -> exact lookup against the registry
      -> corroborate with signature tokens
      -> MATCHED | AMBIGUOUS | TEMPLATE_UNKNOWN

The decision rests **only** on the format number. Signature tokens ("WELDER
IDENTITY CARD", "Qualified Range") adjust confidence and are recorded as
evidence, but they never turn an unmatched page into a matched one. Title text
is the sort of thing that gets copied between forms; the format number is what
identifies a revision, and that is what a template is keyed to.

## Bands, and why it is not header-only

`docs/architecture.md` describes reading the format number from the header
region only, which would be cheaper still. On the real documents it is not
where the number always is:

    requisition sheet   header, y=0.02      NPCIL/QMD/TF/216
    weld data record    header, y=0.06      NPCIL/QMD/TF-114(R0)
    identity card       footer, y=0.46 and y=0.91  (once per card face)
    WPQR                footer, y=0.87 on page 1, y=0.97 on page 2

So the bands are tried in priority order and the whole page is the last
resort. The band that hit is recorded on the result, which keeps the cheap
path cheap and makes it visible when a document needed the expensive one.
This is a deliberate departure from the architecture note, driven by
measurement.

## Failure is a result, not an exception

An unrecognised format number returns TEMPLATE_UNKNOWN, and the caller falls
back to whole-page extraction and flags the document so a human knows which
path produced the values. Two *different* format numbers on one page return
AMBIGUOUS -- also a failure, never a tiebreak, because picking one would be
precisely the confident-wrong-answer failure mode the architecture exists to
avoid.
"""

from __future__ import annotations

import logging

import fitz

from engines.page_geometry import (
    PageWord,
    band_text,
    extract_words,
    find_anchor_matches,
    words_in_band,
)
from knowledge_base.template_registry import (
    REGISTRY_VERSION,
    canonical_keys,
    load_registry,
)
from models.template import (
    BBox,
    ClassificationOutcome,
    ClassificationResult,
    FormTemplate,
)

logger = logging.getLogger(__name__)

__all__ = [
    "REGISTRY_VERSION",
    "SEARCH_BANDS",
    "classify_page",
    "classify_document",
]

# Bands to scan, in priority order. Generous rather than tight: a band that
# misses costs a scan of the next one, whereas a band that clips the format
# number costs a misclassification.
SEARCH_BANDS: list[tuple[str, BBox]] = [
    ("header", BBox(x0=0.0, y0=0.0, x1=1.0, y1=0.25)),
    ("footer", BBox(x0=0.0, y0=0.72, x1=1.0, y1=1.0)),
    ("page", BBox(x0=0.0, y0=0.0, x1=1.0, y1=1.0)),
]

# Confidence for a page whose format number resolved to a registered template
# and which carries no corroborating signature token. Deliberately short of
# certainty: the format number resolved, but nothing else on the page confirms
# it is the form that number names.
BASE_MATCH_CONFIDENCE = 0.70

# Added per matching signature token, capped at CONFIDENCE_CEILING.
SIGNATURE_TOKEN_WEIGHT = 0.10

# Classification never reports certainty. A template match is evidence about a
# scan, and the layers above must stay willing to route to REVIEW.
CONFIDENCE_CEILING = 0.95


def _match_signature_tokens(words: list[PageWord], template: FormTemplate) -> list[str]:
    """Signature tokens from `template` that appear on the page."""
    return [
        token
        for token in template.signature_tokens
        if find_anchor_matches(words, token)
    ]


def _locate_format_text(
    words: list[PageWord], band: BBox
) -> tuple[str | None, BBox | None]:
    """Return the raw line holding a format number in `band`, and its box.

    Used for provenance only -- the decision is made from the canonical key.
    Reporting the line as printed lets a reviewer see what the classifier
    actually read, which matters when the OCR reading is mangled.
    """
    for word in words_in_band(words, band):
        line_band = BBox(
            x0=0.0,
            y0=max(word.bbox.y0 - 0.006, 0.0),
            x1=1.0,
            y1=min(word.bbox.y1 + 0.006, 1.0),
        )
        line_words = words_in_band(words, line_band)
        line = " ".join(w.text for w in line_words)
        if canonical_keys(line):
            boxes = [w.bbox for w in line_words]
            return line, BBox(
                x0=min(b.x0 for b in boxes),
                y0=min(b.y0 for b in boxes),
                x1=max(b.x1 for b in boxes),
                y1=max(b.y1 for b in boxes),
            )
    return None, None


def classify_page(
    page: fitz.Page,
    page_number: int,
    template_dir: str | None = None,
) -> ClassificationResult:
    """Identify which registered form `page` is.

    Never raises on a document problem. An unreadable or unrecognised page is
    a TEMPLATE_UNKNOWN result carrying the reason, because that *is* the
    answer -- the same distinction `engines/pdf_parser.py` draws between
    document problems and infrastructure problems.
    """
    registry = load_registry(template_dir)
    words = extract_words(page)

    if not words:
        return ClassificationResult(
            page_number=page_number,
            outcome=ClassificationOutcome.TEMPLATE_UNKNOWN,
            reason=(
                "No text layer on this page. The page must be rasterised and "
                "read by the vision model before it can be classified."
            ),
        )

    found_keys: list[str] = []
    hit_band: str | None = None
    raw_text: str | None = None
    bbox: BBox | None = None

    for band_name, band in SEARCH_BANDS:
        keys = canonical_keys(band_text(words, band))
        if not keys:
            continue

        found_keys = keys
        hit_band = band_name
        raw_text, bbox = _locate_format_text(words, band)
        break

    if not found_keys:
        return ClassificationResult(
            page_number=page_number,
            outcome=ClassificationOutcome.TEMPLATE_UNKNOWN,
            reason=(
                "No format number found on this page. Falling back to "
                "whole-page extraction; values from this document are flagged "
                "template_unknown."
            ),
        )

    if len(found_keys) > 1:
        return ClassificationResult(
            page_number=page_number,
            outcome=ClassificationOutcome.AMBIGUOUS,
            canonical_candidates=found_keys,
            raw_format_text=raw_text,
            found_in_band=hit_band,
            bbox=bbox,
            reason=(
                f"Page carries {len(found_keys)} different format numbers "
                f"({', '.join(found_keys)}). The form cannot be identified and "
                "the page routes to REVIEW rather than one being chosen."
            ),
        )

    key = found_keys[0]
    template = registry.get(key)

    if template is None:
        return ClassificationResult(
            page_number=page_number,
            outcome=ClassificationOutcome.TEMPLATE_UNKNOWN,
            canonical_candidates=found_keys,
            raw_format_text=raw_text,
            found_in_band=hit_band,
            bbox=bbox,
            reason=(
                f"Format number resolved to '{key}', which no template covers. "
                f"Registered forms: {', '.join(sorted(registry))}. Falling back "
                "to whole-page extraction."
            ),
        )

    matched_tokens = _match_signature_tokens(words, template)
    confidence = min(
        BASE_MATCH_CONFIDENCE + SIGNATURE_TOKEN_WEIGHT * len(matched_tokens),
        CONFIDENCE_CEILING,
    )

    reason = f"Format number '{key}' matched template {template.template_version}."
    if matched_tokens:
        reason += f" Corroborated by {len(matched_tokens)} signature token(s)."
    else:
        reason += (
            " No signature token corroborated it, so confidence is held at the "
            "format-number-only floor."
        )
    if not template.verified:
        reason += (
            " Template regions are UNVERIFIED against a reviewed form and must "
            "be flagged wherever these values are shown."
        )

    return ClassificationResult(
        page_number=page_number,
        outcome=ClassificationOutcome.MATCHED,
        canonical_key=key,
        form_type=template.form_type,
        template_version=template.template_version,
        canonical_candidates=found_keys,
        raw_format_text=raw_text,
        found_in_band=hit_band,
        bbox=bbox,
        matched_signature_tokens=matched_tokens,
        confidence=confidence,
        reason=reason,
        template_verified=template.verified,
    )


def classify_document(
    file_bytes: bytes,
    template_dir: str | None = None,
) -> list[ClassificationResult]:
    """Classify every page of a PDF.

    Pages are classified independently and deliberately so. One PDF in the
    sample set holds two different welders' cards, and a package can arrive as
    a single scanned bundle -- assuming one form per file would merge two
    welders into one record.

    Raises:
        ValueError: The bytes could not be opened as a PDF. An unopenable file
            is an infrastructure problem, not a document problem, so unlike
            every other failure here it raises.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Could not open bytes as a PDF: {exc}") from exc

    try:
        return [
            classify_page(doc.load_page(i), i + 1, template_dir)
            for i in range(doc.page_count)
        ]
    finally:
        doc.close()
