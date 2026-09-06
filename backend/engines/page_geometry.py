"""Page word geometry: extraction, normalisation, anchor resolution.

Shared by `engines/form_classifier.py` and `engines/region_extractor.py`.

Everything here works in **normalised coordinates** (0..1 fractions of page
width and height) rather than PDF points, because the same form scans to
different page sizes -- the welder identity card arrives as both 528x792 and
542x792 points. Normalising at the boundary means every template region, every
anchor search band and every stored bounding box is comparable across scans.

Words are read in **spatial** order (top to bottom, then left to right) rather
than the PDF's own reading order. On the sample WPQR the embedded order is
badly scrambled -- labels first, then both value columns interleaved -- so
reading order cannot be trusted to put a label next to its value, or even to
keep a format number next to its family token.
"""

from __future__ import annotations

import re

import fitz
from pydantic import BaseModel, Field

from models.template import BBox

# Rows within this fraction of page height of each other are treated as one
# line when text is reassembled. Sized from the sample scans: body text runs
# 12-16pt line spacing on a 792pt page, i.e. 0.015-0.020, so half of that
# groups a line without merging two.
LINE_TOLERANCE = 0.010


class PageWord(BaseModel):
    """One word and where it sits, in normalised page coordinates."""

    text: str
    bbox: BBox

    @property
    def x_centre(self) -> float:
        return (self.bbox.x0 + self.bbox.x1) / 2.0

    @property
    def y_centre(self) -> float:
        return (self.bbox.y0 + self.bbox.y1) / 2.0


def normalise_text(text: str) -> str:
    """Uppercase, strip punctuation, collapse whitespace.

    Anchor matching runs on this form so that a label survives the punctuation
    and spacing noise an OCR text layer adds -- the identity card's front face
    reads "WELDER NAME :" on one scan and "WELDER NAME:" on the other, and both
    must match the anchor "WELDER NAME".

    Note what this deliberately does NOT do: it does not touch letters. Anchor
    matching stays exact on characters, so a genuinely different label can
    never match. Character-level OCR confusions are handled by listing the
    mangled reading in the anchor's `alternates`, which keeps the match table
    auditable rather than hiding it behind a similarity score.
    """
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


def extract_words(page: fitz.Page) -> list[PageWord]:
    """Return every word on the page in normalised coordinates, spatially sorted.

    Words are clamped to the page rectangle. The sample identity card contains
    a word whose OCR bounding box starts at x = -0.015 (an artefact of the scan
    deskew), which would fail BBox validation unclamped.
    """
    rect = page.rect
    width = float(rect.width)
    height = float(rect.height)
    if width <= 0 or height <= 0:  # pragma: no cover - malformed page
        return []

    words: list[PageWord] = []
    for x0, y0, x1, y1, text, *_ in page.get_text("words"):
        if not text.strip():
            continue

        nx0 = min(max(float(x0) / width, 0.0), 1.0)
        nx1 = min(max(float(x1) / width, 0.0), 1.0)
        ny0 = min(max(float(y0) / height, 0.0), 1.0)
        ny1 = min(max(float(y1) / height, 0.0), 1.0)

        # A word clamped to zero width or height carries no usable geometry.
        if nx1 <= nx0 or ny1 <= ny0:
            continue

        words.append(
            PageWord(text=text, bbox=BBox(x0=nx0, y0=ny0, x1=nx1, y1=ny1))
        )

    words.sort(key=lambda w: (round(w.bbox.y0 / LINE_TOLERANCE), w.bbox.x0))
    return words


def words_in_band(words: list[PageWord], band: BBox | None) -> list[PageWord]:
    """Words whose centre falls inside `band`. All words when band is None.

    Centre-point containment rather than full overlap: a value box drawn tight
    around printed text will clip the ascenders and descenders of the words it
    is meant to contain, and a full-containment test would then drop them.
    """
    if band is None:
        return list(words)

    return [
        w
        for w in words
        if band.x0 <= w.x_centre <= band.x1 and band.y0 <= w.y_centre <= band.y1
    ]


def band_text(words: list[PageWord], band: BBox | None = None) -> str:
    """Reassemble words in a band into text, one line per visual row."""
    selected = words_in_band(words, band)
    if not selected:
        return ""

    lines: list[list[str]] = []
    current_row: int | None = None

    for word in selected:
        row = round(word.bbox.y0 / LINE_TOLERANCE)
        if row != current_row:
            lines.append([])
            current_row = row
        lines[-1].append(word.text)

    return "\n".join(" ".join(line) for line in lines)


def union_bbox(words: list[PageWord]) -> BBox | None:
    """Smallest box containing every word given."""
    if not words:
        return None
    return BBox(
        x0=min(w.bbox.x0 for w in words),
        y0=min(w.bbox.y0 for w in words),
        x1=max(w.bbox.x1 for w in words),
        y1=max(w.bbox.y1 for w in words),
    )


def find_anchor_matches(
    words: list[PageWord],
    anchor_text: str,
    band: BBox | None = None,
) -> list[BBox]:
    """Every place `anchor_text` appears, as bounding boxes, in reading order.

    Matching is done on a normalised word sequence: the anchor is split into
    normalised tokens and slid across the page's normalised tokens. This makes
    the match independent of how the OCR layer chose to split or punctuate the
    label -- "WELDER NAME :" and "WELDER NAME:" both match "WELDER NAME" -- while
    keeping it exact on the letters themselves.
    """
    needle = normalise_text(anchor_text).split()
    if not needle:
        return []

    candidates = words_in_band(words, band)

    # One entry per candidate word: its normalised tokens and its box. A word
    # can normalise to several tokens ("NO.:TPL/GHAVPW-71" -> "NO TPL GHAVPW
    # 71") or to none at all (a stray "|"), so the token stream and the word
    # list are not one-to-one and the mapping has to be kept explicitly.
    tokens: list[str] = []
    owners: list[BBox] = []
    for word in candidates:
        for token in normalise_text(word.text).split():
            tokens.append(token)
            owners.append(word.bbox)

    matches: list[BBox] = []
    span = len(needle)
    index = 0
    while index + span <= len(tokens):
        if tokens[index : index + span] == needle:
            boxes = owners[index : index + span]
            matches.append(
                BBox(
                    x0=min(b.x0 for b in boxes),
                    y0=min(b.y0 for b in boxes),
                    x1=max(b.x1 for b in boxes),
                    y1=max(b.y1 for b in boxes),
                )
            )
            # Advance past this match so overlapping hits are not double
            # counted -- otherwise "NO NO" would report two matches for "NO".
            index += span
        else:
            index += 1

    return matches


class ResolvedAnchor(BaseModel):
    """Where an anchor was found, and by which spelling."""

    bbox: BBox
    matched_text: str = Field(
        ..., description="The anchor spelling that hit: `text` or one of `alternates`."
    )
    occurrence: int


def resolve_anchor(
    words: list[PageWord],
    anchor_text: str,
    alternates: list[str],
    occurrence: int,
    band: BBox | None = None,
) -> ResolvedAnchor | None:
    """Locate one anchor, or return None.

    The primary spelling is tried first and each alternate only if it misses,
    so a template that lists an OCR misread still prefers the correct reading
    when both are present on the page.

    Returns None rather than raising: a missing anchor is a recoverable
    condition that downgrades the field to its fallback rect and lowers
    confidence. It is the caller's job to record that, not to fail the parse.
    """
    for spelling in [anchor_text, *alternates]:
        matches = find_anchor_matches(words, spelling, band)
        if len(matches) > occurrence:
            return ResolvedAnchor(
                bbox=matches[occurrence],
                matched_text=spelling,
                occurrence=occurrence,
            )
    return None
