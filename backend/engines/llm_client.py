"""LLM client abstraction.

Nothing outside this module talks to a model provider. Services and engines
depend on the `LLMClient` interface, so the model can be swapped -- a different
Nemotron build, a different provider entirely -- by changing configuration
rather than business logic.

Two implementations ship:

* `NvidiaLLMClient` -- the real one, against NVIDIA NIM's OpenAI-compatible
  endpoint.
* `MockLLMClient` -- returns canned responses, so the whole pipeline is
  testable offline, free, and deterministically. Every downstream test uses it.

The model's response is parsed and validated against `ExtractionResult` before
any caller sees it. A response that will not parse is retried once, then the
call fails as REVIEW_REQUIRED rather than returning a half-understood result.
"""

from __future__ import annotations

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Any

from pydantic import ValidationError

from config import settings
from models.extraction import ExtractionResult
from utils.prompts import ACTIVE_EXTRACTION_PROMPT_VERSION, build_extraction_messages

logger = logging.getLogger(__name__)

MAX_PARSE_ATTEMPTS = 2

# Some models wrap JSON in markdown fences despite instructions not to.
_FENCE_PATTERN = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


class LLMError(Exception):
    """The provider call failed, or its output could not be used."""


class ExtractionFailure(LLMError):
    """The model's output could not be parsed into a valid ExtractionResult.

    Callers must treat this as REVIEW_REQUIRED. It is never a reason to
    fabricate an empty result and continue as though extraction succeeded.
    """


class LLMResponse:
    """An extraction result plus the metadata needed for cost and eval tracking."""

    def __init__(
        self,
        result: ExtractionResult,
        *,
        model: str,
        prompt_version: str,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        latency_seconds: float | None = None,
        attempts: int = 1,
    ) -> None:
        self.result = result
        self.model = model
        self.prompt_version = prompt_version
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.latency_seconds = latency_seconds
        self.attempts = attempts

    @property
    def total_tokens(self) -> int | None:
        if self.prompt_tokens is None and self.completion_tokens is None:
            return None
        return (self.prompt_tokens or 0) + (self.completion_tokens or 0)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences a model may have wrapped its JSON in."""
    return _FENCE_PATTERN.sub("", text).strip()


def _extract_json_object(text: str) -> str:
    """Isolate the outermost JSON object from a response.

    Tolerates leading or trailing prose without accepting it as data: only the
    braces-delimited object is parsed.
    """
    cleaned = _strip_fences(text)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ExtractionFailure("No JSON object found in model response")
    return cleaned[start : end + 1]


def parse_extraction_response(raw: str) -> ExtractionResult:
    """Parse and validate a raw model response.

    Raises:
        ExtractionFailure: The response is not valid JSON, or does not satisfy
            the extraction schema.
    """
    payload = _extract_json_object(raw)

    try:
        data: Any = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ExtractionFailure(f"Model response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ExtractionFailure("Model response was not a JSON object")

    try:
        return ExtractionResult.model_validate(data)
    except ValidationError as exc:
        raise ExtractionFailure(f"Model response failed schema validation: {exc}") from exc


class LLMClient(ABC):
    """Interface every model provider implementation satisfies."""

    @abstractmethod
    def complete(self, messages: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
        """Send chat messages and return (raw text, provider metadata)."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier of the model in use, recorded on every audit."""

    def extract_structured(
        self,
        document_text: str,
        prompt_version: str = ACTIVE_EXTRACTION_PROMPT_VERSION,
    ) -> LLMResponse:
        """Extract certificate values from document text.

        Retries once on a parse failure -- models occasionally emit a stray
        prefix or a truncated object, and a second attempt is cheaper than
        sending a document to manual review.

        Raises:
            ExtractionFailure: Parsing failed on every attempt.
        """
        messages = build_extraction_messages(document_text, prompt_version)
        started = time.monotonic()
        last_error: Exception | None = None

        for attempt in range(1, MAX_PARSE_ATTEMPTS + 1):
            try:
                raw, meta = self.complete(messages)
            except Exception as exc:
                raise LLMError(f"Model call failed: {exc}") from exc

            try:
                result = parse_extraction_response(raw)
            except ExtractionFailure as exc:
                last_error = exc
                logger.warning(
                    "Extraction parse failed (attempt %s/%s): %s",
                    attempt,
                    MAX_PARSE_ATTEMPTS,
                    exc,
                )
                continue

            elapsed = time.monotonic() - started
            logger.info(
                "Extraction ok: model=%s prompt=%s attempts=%s tokens=%s latency=%.2fs",
                self.model_name,
                prompt_version,
                attempt,
                meta.get("total_tokens"),
                elapsed,
            )
            return LLMResponse(
                result,
                model=self.model_name,
                prompt_version=prompt_version,
                prompt_tokens=meta.get("prompt_tokens"),
                completion_tokens=meta.get("completion_tokens"),
                latency_seconds=elapsed,
                attempts=attempt,
            )

        raise ExtractionFailure(
            f"Could not parse a valid extraction after {MAX_PARSE_ATTEMPTS} "
            f"attempts: {last_error}"
        )


class NvidiaLLMClient(LLMClient):
    """Nemotron via NVIDIA NIM's OpenAI-compatible endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
    ) -> None:
        self._api_key = api_key or settings.NVIDIA_API_KEY
        self._base_url = base_url or settings.NVIDIA_BASE_URL
        self._model = model or settings.NVIDIA_MODEL
        self._temperature = temperature

        if not self._api_key:
            raise LLMError("NVIDIA_API_KEY is not configured")

        # Imported lazily so the mock path, and every test, runs without the
        # openai package installed.
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise LLMError(
                "The 'openai' package is required for NvidiaLLMClient"
            ) from exc

        self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)

    @property
    def model_name(self) -> str:
        return self._model

    def complete(self, messages: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
        """Call the provider and return the raw text plus token usage."""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self._temperature,
        )

        content = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        meta: dict[str, Any] = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }
        return content, meta


class MockLLMClient(LLMClient):
    """Returns canned responses. Used by every offline test.

    Accepts either a raw JSON string or a dict, so tests can exercise the
    parsing and validation path as well as the happy path.
    """

    def __init__(
        self,
        response: str | dict[str, Any] | None = None,
        responses: list[str | dict[str, Any]] | None = None,
        model: str = "mock-model",
    ) -> None:
        if responses is None:
            responses = [response if response is not None else {}]
        self._responses = responses
        self._model = model
        self.calls: list[list[dict[str, str]]] = []

    @property
    def model_name(self) -> str:
        return self._model

    def complete(self, messages: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
        """Return the next canned response, repeating the last one when exhausted."""
        self.calls.append(messages)
        index = min(len(self.calls) - 1, len(self._responses) - 1)
        payload = self._responses[index]
        raw = payload if isinstance(payload, str) else json.dumps(payload)
        return raw, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def get_llm_client() -> LLMClient:
    """Return the configured client.

    Falls back to the mock when no API key is set, so the pipeline is runnable
    end to end before credentials exist.
    """
    if settings.NVIDIA_API_KEY:
        return NvidiaLLMClient()

    logger.warning("NVIDIA_API_KEY not set - falling back to MockLLMClient")
    return MockLLMClient()
