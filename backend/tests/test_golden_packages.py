"""Golden package regression tests against the real sample documents.

`docs/practices.md` asks for real packages with hand-written expected findings,
run on every commit -- because 127 passing unit tests on synthetic inputs said
nothing about how the parser handles a landscape scan with a rubber stamp over
the heat number.

The real documents can never be committed: they carry welder photographs, full
names, ID numbers and signatures from an operating nuclear site (CLAUDE.md
section 10). So this module runs against whatever is present in the gitignored
fixtures directory and **skips** when it is absent. It is a local and
pre-commit gate, not a CI gate, and that is the trade the data handling rules
force.

Two consequences shape what is asserted here:

**No document content appears in this file.** No welder name, no ID, no coupon
number. The assertions are structural -- which template matched, how firmly
regions resolved, whether the same bytes produce the same answer twice. A test
that hardcoded a welder's name would be committing the very data the fixtures
directory exists to keep out of git.

**Value-level expectations live beside the fixtures, not here.** Drop a
`golden_expectations.json` into the fixtures directory to assert specific
field values; it is gitignored along with everything else there. The schema is
documented in `_load_expectations` below.
"""

from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from engines.form_classifier import classify_page
from engines.region_extractor import extract_page
from knowledge_base.template_registry import get_template
from models.template import ClassificationOutcome

# Searched in order. `fixtures/` is the documented home (CLAUDE.md section 10);
# `docs/` is where the sample package currently sits and is gitignored too.
_REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIRS = [_REPO_ROOT / "fixtures", _REPO_ROOT / "docs"]

# Copyrighted -- read to build rule tables, never parsed as a package document.
EXCLUDED = ("section ix",)


def _fixture_pdfs() -> list[Path]:
    for directory in FIXTURE_DIRS:
        if not directory.is_dir():
            continue
        found = [
            p
            for p in sorted(directory.glob("*.pdf"))
            if not any(token in p.name.lower() for token in EXCLUDED)
        ]
        if found:
            return found
    return []


def _load_expectations() -> dict:
    """Optional value-level expectations, stored beside the fixtures.

    Schema, keyed by "<filename>::<1-indexed page>":

        {
          "welder identity card .pdf::1": {
            "canonical_key": "TF-127-R0",
            "fields": {"welder_name": "...", "coupon_no": "..."}
          }
        }
    """
    for directory in FIXTURE_DIRS:
        candidate = directory / "golden_expectations.json"
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    return {}


FIXTURES = _fixture_pdfs()
EXPECTATIONS = _load_expectations()

pytestmark = pytest.mark.skipif(
    not FIXTURES,
    reason=(
        "No fixture PDFs found. Real welder packages are gitignored; place "
        "them in fixtures/ to run the golden regression suite."
    ),
)


def _pages():
    """Yield (path, page_number) for every fixture page."""
    for path in FIXTURES:
        doc = fitz.open(path)
        try:
            count = doc.page_count
        finally:
            doc.close()
        for number in range(1, count + 1):
            yield path, number


class TestClassificationIsStable:
    def test_every_page_reaches_a_defined_outcome(self):
        """No page may crash, hang, or return a half-answer.

        A page the classifier cannot identify is a TEMPLATE_UNKNOWN result
        carrying a reason -- never an exception and never a silent pass.
        """
        for path, number in _pages():
            doc = fitz.open(path)
            try:
                result = classify_page(doc.load_page(number - 1), number)
            finally:
                doc.close()

            assert result.outcome in set(ClassificationOutcome)
            assert result.page_number == number
            if not result.matched:
                assert result.reason, f"{path.name} p{number} gave no reason"

    def test_no_page_is_ambiguous(self):
        """Two different format numbers on one page means we cannot tell.

        None of the sample documents should hit this. If one starts to, the
        canonicalisation rules have grown too loose and are matching text that
        is not a format number.
        """
        for path, number in _pages():
            doc = fitz.open(path)
            try:
                result = classify_page(doc.load_page(number - 1), number)
            finally:
                doc.close()

            assert result.outcome is not ClassificationOutcome.AMBIGUOUS, (
                f"{path.name} p{number} resolved to multiple format numbers: "
                f"{result.canonical_candidates}"
            )

    def test_a_matched_page_names_a_registered_template(self):
        for path, number in _pages():
            doc = fitz.open(path)
            try:
                result = classify_page(doc.load_page(number - 1), number)
            finally:
                doc.close()

            if result.matched:
                assert result.canonical_key
                assert get_template(result.canonical_key)
                assert result.confidence > 0.0

    def test_at_least_one_page_matches(self):
        """Guards against a change that silently classifies nothing.

        Every assertion above passes vacuously if the classifier stops matching
        altogether, which is exactly the regression most worth catching.
        """
        matched = 0
        for path, number in _pages():
            doc = fitz.open(path)
            try:
                if classify_page(doc.load_page(number - 1), number).matched:
                    matched += 1
            finally:
                doc.close()

        assert matched > 0, "classifier matched no page of any fixture"


class TestExtractionIsStable:
    def test_matched_pages_resolve_their_required_fields(self):
        """Most required fields must resolve through their anchors.

        Not all of them: OCR sometimes merges a label into its value, and the
        extractor is expected to recover from the fallback rect and flag it.
        The bar is that anchoring works in the large, so a template whose
        anchors have gone stale fails here rather than degrading quietly.
        """
        for path, number in _pages():
            doc = fitz.open(path)
            try:
                page = doc.load_page(number - 1)
                result = classify_page(page, number)
                if not result.matched:
                    continue
                extraction = extract_page(
                    page, get_template(result.canonical_key), number
                )
            finally:
                doc.close()

            readable = [f for f in extraction.fields if f.value is not None]
            assert readable, f"{path.name} p{number} read no field at all"

            anchored = [f for f in readable if f.confidence >= 0.9]
            assert len(anchored) >= len(readable) * 0.75, (
                f"{path.name} p{number}: only {len(anchored)}/{len(readable)} "
                "fields resolved through their anchors"
            )

    def test_checkboxes_never_yield_a_value(self):
        """The dual CV/vision read is build step 2 and has no stand-in.

        The text layer does render a tick as a stray "v" on the sample WPQR.
        Reading it would be a third, unsanctioned method.
        """
        for path, number in _pages():
            doc = fitz.open(path)
            try:
                page = doc.load_page(number - 1)
                result = classify_page(page, number)
                if not result.matched:
                    continue
                extraction = extract_page(
                    page, get_template(result.canonical_key), number
                )
            finally:
                doc.close()

            for field in extraction.fields:
                if field.value_kind.value == "checkbox":
                    assert field.value is None
                    assert field.needs_review is True

    def test_every_value_carries_its_provenance(self):
        """A finding that cannot be traced to a region of a page is not a finding."""
        for path, number in _pages():
            doc = fitz.open(path)
            try:
                page = doc.load_page(number - 1)
                result = classify_page(page, number)
                if not result.matched:
                    continue
                extraction = extract_page(
                    page, get_template(result.canonical_key), number
                )
            finally:
                doc.close()

            for field in extraction.fields:
                assert field.template_version
                assert field.page == number
                if field.value is not None:
                    assert field.bbox is not None


class TestDeterminism:
    def test_the_same_page_twice_gives_byte_identical_output(self):
        """Vision models drift even at temperature 0.

        This path is deterministic by construction and must stay that way: a QA
        tool that gives two answers to one document is finished.
        """
        for path, number in _pages():
            dumps = []
            for _ in range(2):
                doc = fitz.open(path)
                try:
                    page = doc.load_page(number - 1)
                    result = classify_page(page, number)
                    payload = result.model_dump_json()
                    if result.matched:
                        payload += extract_page(
                            page, get_template(result.canonical_key), number
                        ).model_dump_json()
                finally:
                    doc.close()
                dumps.append(payload)

            assert dumps[0] == dumps[1], f"{path.name} p{number} was not deterministic"


class TestDeclaredExpectations:
    """Value-level assertions, driven by a gitignored expectations file."""

    def test_expected_values_match(self):
        if not EXPECTATIONS:
            pytest.skip(
                "No golden_expectations.json beside the fixtures. Add one to "
                "assert specific field values; it stays gitignored."
            )

        for key, expected in EXPECTATIONS.items():
            filename, _, page_text = key.partition("::")
            number = int(page_text)
            path = next((p for p in FIXTURES if p.name == filename), None)
            assert path is not None, f"expectation names a missing fixture: {filename}"

            doc = fitz.open(path)
            try:
                page = doc.load_page(number - 1)
                result = classify_page(page, number)
                assert result.canonical_key == expected.get("canonical_key"), (
                    f"{key}: expected {expected.get('canonical_key')}, "
                    f"got {result.canonical_key}"
                )
                if not expected.get("fields"):
                    continue
                extraction = extract_page(
                    page, get_template(result.canonical_key), number
                )
            finally:
                doc.close()

            for name, want in expected["fields"].items():
                field = extraction.by_name(name)
                assert field is not None, f"{key}: template has no field '{name}'"
                assert field.value == want, (
                    f"{key}: field '{name}' expected {want!r}, got {field.value!r}"
                )
