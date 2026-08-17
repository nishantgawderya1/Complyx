"""Tests for the LLM client abstraction and response parsing.

The parsing layer is the boundary between an untrusted model response and the
rest of the system. Anything that does not fit the schema must be rejected, not
partially trusted.
"""

import json

import pytest

from engines.llm_client import (
    ExtractionFailure,
    LLMClient,
    MockLLMClient,
    parse_extraction_response,
)
from models.extraction import Confidence

VALID_PAYLOAD = {
    "document_type": "MTC",
    "material_grade": {
        "value": "70",
        "unit": None,
        "page": 1,
        "source_text": "GRADE 70",
        "confidence": "high",
    },
    "tensile_strength": {
        "value": 480,
        "unit": "MPa",
        "page": 1,
        "source_text": "Tensile 480 MPa",
        "confidence": "high",
    },
    "uncertain_fields": [],
}


class TestParseExtractionResponse:
    def test_parses_clean_json(self):
        result = parse_extraction_response(json.dumps(VALID_PAYLOAD))

        assert result.material_grade.value == "70"
        assert result.tensile_strength.as_float() == 480.0
        assert result.tensile_strength.confidence is Confidence.HIGH

    def test_strips_markdown_fences(self):
        """Models wrap JSON in fences despite being told not to."""
        fenced = f"```json\n{json.dumps(VALID_PAYLOAD)}\n```"
        assert parse_extraction_response(fenced).material_grade.value == "70"

    def test_tolerates_surrounding_prose(self):
        noisy = f"Here is the result:\n{json.dumps(VALID_PAYLOAD)}\nHope that helps!"
        assert parse_extraction_response(noisy).material_grade.value == "70"

    def test_rejects_response_with_no_json(self):
        with pytest.raises(ExtractionFailure):
            parse_extraction_response("I could not read this document.")

    def test_rejects_malformed_json(self):
        with pytest.raises(ExtractionFailure):
            parse_extraction_response('{"material_grade": {')

    def test_rejects_json_that_is_not_an_object(self):
        with pytest.raises(ExtractionFailure):
            parse_extraction_response("[1, 2, 3]")

    def test_rejects_invalid_confidence_value(self):
        """Schema validation is the guard against a plausible-looking wrong shape."""
        payload = json.loads(json.dumps(VALID_PAYLOAD))
        payload["tensile_strength"]["confidence"] = "pretty sure"

        with pytest.raises(ExtractionFailure):
            parse_extraction_response(json.dumps(payload))

    def test_missing_fields_default_to_not_found(self):
        result = parse_extraction_response('{"document_type": "MTC"}')

        assert result.yield_strength.confidence is Confidence.NOT_FOUND
        assert result.yield_strength.is_present is False


class TestExtractedFieldBehaviour:
    def test_numeric_strings_are_coerced(self):
        result = parse_extraction_response(
            '{"tensile_strength": {"value": "1,350", "unit": "MPa", '
            '"confidence": "high"}}'
        )
        assert result.tensile_strength.as_float() == 1350.0

    def test_qualifier_text_is_not_a_number(self):
        """'265 min' is a specification restatement, not a measured value."""
        result = parse_extraction_response(
            '{"yield_strength": {"value": "265 min", "confidence": "high"}}'
        )
        assert result.yield_strength.as_float() is None

    def test_low_confidence_is_present_but_not_reliable(self):
        result = parse_extraction_response(
            '{"yield_strength": {"value": 265, "unit": "MPa", "confidence": "low"}}'
        )
        assert result.yield_strength.is_present is True
        assert result.yield_strength.is_reliable is False


class TestMockClient:
    def test_returns_configured_response(self):
        client = MockLLMClient(response=VALID_PAYLOAD)
        response = client.extract_structured("document text")

        assert response.result.material_grade.value == "70"
        assert response.model == "mock-model"
        assert response.attempts == 1

    def test_is_an_llm_client(self):
        assert isinstance(MockLLMClient(), LLMClient)

    def test_document_text_reaches_the_user_message_only(self):
        """Document content must never enter the system prompt."""
        client = MockLLMClient(response=VALID_PAYLOAD)
        client.extract_structured("SECRET DOCUMENT BODY")

        system, user = client.calls[0]
        assert system["role"] == "system"
        assert "SECRET DOCUMENT BODY" not in system["content"]
        assert "SECRET DOCUMENT BODY" in user["content"]
        assert "---DOCUMENT START---" in user["content"]

    def test_retries_once_then_succeeds(self):
        client = MockLLMClient(responses=["not json at all", json.dumps(VALID_PAYLOAD)])
        response = client.extract_structured("text")

        assert response.attempts == 2
        assert response.result.material_grade.value == "70"

    def test_gives_up_after_repeated_parse_failures(self):
        """Persistent failure must raise, not return an empty result."""
        client = MockLLMClient(responses=["garbage", "still garbage"])

        with pytest.raises(ExtractionFailure):
            client.extract_structured("text")

    def test_prompt_version_is_recorded(self):
        client = MockLLMClient(response=VALID_PAYLOAD)
        response = client.extract_structured("text")
        assert response.prompt_version == "extraction_v1"
