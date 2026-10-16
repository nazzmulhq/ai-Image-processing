"""Gemini integration (google-genai SDK, `client.models.generate_content`).

Verified against google-genai 2.31.0: `types.GenerateContentConfig` fields
`response_mime_type`, `response_json_schema`, `response_modalities`, `image_config`,
`http_options` (timeout in ms); `types.Part.from_bytes(data=, mime_type=)`;
`errors.APIError` (`.code`, `.status`, `.details`); SDK retries are off unless
`retry_options` is set, so all retries here are our own.

Calls use the SDK's async client (`client.aio`) so they never block the event loop. An
asyncio semaphore caps concurrent Gemini calls per process; retries use exponential backoff
with full jitter and honour the server's RetryInfo delay.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError, field_validator

from app.core.concurrency import backoff_delay
from app.core.config import Settings
from app.core.errors import ErrorCode

logger = logging.getLogger(__name__)

DETECTION_PROMPT = (
    "Detect the distinct, clearly visible objects in this image. Respond with JSON only, "
    "matching the provided schema.\n"
    "For each object return:\n"
    "- label: a short noun phrase (e.g. 'red bicycle')\n"
    "- category: a broad class such as person, animal, vehicle, food, furniture, "
    "electronics, plant, building, clothing, text or other\n"
    "- description: one short sentence about its appearance\n"
    "- box_2d: [ymin, xmin, ymax, xmax] as integers normalised to 0-1000. Include box_2d "
    "only when you can localise the object; omit it otherwise.\n"
    "Also return main_subject: a short phrase naming the main subject of the image.\n"
    "List at most 25 objects. Do not include objects that are not visible."
)

DETECTION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "main_subject": {"type": "string"},
        "objects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "category": {"type": "string"},
                    "description": {"type": "string"},
                    "box_2d": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                },
                "required": ["label"],
            },
        },
    },
    "required": ["objects"],
}

MAX_OBJECTS = 50
MAX_EDIT_OUTPUT_BYTES = 40 * 1024 * 1024

_SAFETY_FINISH_REASONS = {
    types.FinishReason.SAFETY, types.FinishReason.BLOCKLIST,
    types.FinishReason.PROHIBITED_CONTENT, types.FinishReason.SPII,
    types.FinishReason.IMAGE_SAFETY, types.FinishReason.IMAGE_PROHIBITED_CONTENT,
    types.FinishReason.RECITATION, types.FinishReason.IMAGE_RECITATION,
}
_RETRY_DELAY_RE = re.compile(r"^(\d+(?:\.\d+)?)s$")


class GeminiError(Exception):
    def __init__(self, code: ErrorCode, message: str, *, retryable: bool = False,
                 retry_after: float | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.retry_after = retry_after


# --- Result types ----------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class NormalizedBox:
    """Bounding box as fractions (0..1) of image width/height."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float


@dataclass(frozen=True, slots=True)
class Detection:
    label: str
    category: str | None
    description: str | None
    box: NormalizedBox | None
    # Gemini does not return calibrated confidence scores; always None.
    confidence: float | None = None


@dataclass(frozen=True)
class DetectionResult:
    model: str
    main_subject: str | None
    objects: list[Detection] = field(default_factory=list)
    invalid_boxes: int = 0
    truncated_objects: int = 0


@dataclass(frozen=True, slots=True)
class EditedImage:
    data: bytes
    mime_type: str
    model: str


class GeminiService(Protocol):
    async def detect_objects(self, image: bytes, mime_type: str) -> DetectionResult: ...

    async def edit_image(self, image: bytes, mime_type: str, *, prompt: str,
                         aspect_ratio: str | None) -> EditedImage: ...

    async def aclose(self) -> None: ...


# --- Model-output validation -----------------------------------------------------------------

def _clean_text(value: Any, max_len: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("expected a string")
    text = " ".join(value.split())
    return text[:max_len] if text else None


class _RawObject(BaseModel):
    label: str
    category: str | None = None
    description: str | None = None
    box_2d: Any = None  # validated separately so one bad box doesn't reject the response

    @field_validator("label", mode="before")
    @classmethod
    def _label(cls, value: Any) -> str:
        text = _clean_text(value, 200)
        if not text:
            raise ValueError("label must be a non-empty string")
        return text

    @field_validator("category", mode="before")
    @classmethod
    def _category(cls, value: Any) -> str | None:
        return _clean_text(value, 100)

    @field_validator("description", mode="before")
    @classmethod
    def _description(cls, value: Any) -> str | None:
        return _clean_text(value, 1000)


class _RawDetection(BaseModel):
    main_subject: str | None = None
    objects: list[_RawObject]

    @field_validator("main_subject", mode="before")
    @classmethod
    def _main_subject(cls, value: Any) -> str | None:
        return _clean_text(value, 500)


def normalize_box(box_2d: Any) -> NormalizedBox | None:
    """Validate a Gemini `[ymin, xmin, ymax, xmax]` box on the 0-1000 scale.

    Returns None for anything invalid (wrong shape, non-numeric, out of range, empty area)
    - coordinates are never guessed or clamped into existence.
    """
    if not isinstance(box_2d, (list, tuple)) or len(box_2d) != 4:
        return None
    values: list[float] = []
    for v in box_2d:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            return None
        if v < 0 or v > 1000:
            return None
        values.append(float(v))
    y_min, x_min, y_max, x_max = values
    if not (y_min < y_max and x_min < x_max):
        return None
    return NormalizedBox(x_min=x_min / 1000, y_min=y_min / 1000,
                         x_max=x_max / 1000, y_max=y_max / 1000)


def parse_detection_payload(text: str | None, *, model: str) -> DetectionResult:
    if not text or not text.strip():
        raise GeminiError(ErrorCode.GEMINI_INVALID_RESPONSE,
                          "The AI model returned an empty detection response.")
    try:
        raw = _RawDetection.model_validate_json(text)
    except ValidationError as exc:
        raise GeminiError(ErrorCode.GEMINI_INVALID_RESPONSE,
                          "The AI model returned malformed detection output.") from exc
    objects: list[Detection] = []
    invalid = 0
    for item in raw.objects[:MAX_OBJECTS]:
        box = normalize_box(item.box_2d) if item.box_2d is not None else None
        if item.box_2d is not None and box is None:
            invalid += 1
        objects.append(Detection(label=item.label, category=item.category,
                                 description=item.description, box=box))
    return DetectionResult(model=model, main_subject=raw.main_subject, objects=objects,
                           invalid_boxes=invalid,
                           truncated_objects=max(0, len(raw.objects) - MAX_OBJECTS))


# --- Error classification --------------------------------------------------------------------

def _retry_delay_from_details(details: Any) -> float | None:
    try:
        error = details.get("error", details) if isinstance(details, dict) else {}
        for item in error.get("details", []) or []:
            if str(item.get("@type", "")).endswith("RetryInfo"):
                match = _RETRY_DELAY_RE.match(str(item.get("retryDelay", "")))
                if match:
                    return min(60.0, float(match.group(1)))
    except (AttributeError, TypeError, ValueError):
        return None
    return None


def classify_api_error(exc: genai_errors.APIError) -> GeminiError:
    code = int(exc.code or 0)
    status = (exc.status or "").upper()
    if code == 429 or status == "RESOURCE_EXHAUSTED":
        return GeminiError(ErrorCode.GEMINI_RATE_LIMITED,
                           "The AI service is rate limited. Please retry later.",
                           retryable=True, retry_after=_retry_delay_from_details(exc.details))
    if code in (500, 502, 503, 504) or status in ("UNAVAILABLE", "INTERNAL"):
        return GeminiError(ErrorCode.GEMINI_UNAVAILABLE,
                           "The AI service is temporarily unavailable.", retryable=True)
    if code == 408 or status == "DEADLINE_EXCEEDED":
        return GeminiError(ErrorCode.GEMINI_TIMEOUT, "The AI service timed out.", retryable=True)
    if code in (401, 403, 404) or status in ("PERMISSION_DENIED", "UNAUTHENTICATED", "NOT_FOUND"):
        logger.error("gemini_configuration_error", extra={"gemini_status": status,
                                                          "gemini_code": code})
        return GeminiError(ErrorCode.GEMINI_CONFIGURATION_ERROR,
                           "The AI service is unavailable due to a server configuration problem.")
    return GeminiError(ErrorCode.GEMINI_REQUEST_REJECTED,
                       "The AI service rejected the request.")


def raise_if_blocked(response: types.GenerateContentResponse) -> None:
    feedback = response.prompt_feedback
    if feedback is not None and feedback.block_reason not in (
        None, types.BlockedReason.BLOCKED_REASON_UNSPECIFIED
    ):
        raise GeminiError(ErrorCode.GEMINI_SAFETY_BLOCKED,
                          "The AI service declined to process this image (safety filter).")
    if not response.candidates:
        raise GeminiError(ErrorCode.GEMINI_INVALID_RESPONSE,
                          "The AI service returned no result.")
    if response.candidates[0].finish_reason in _SAFETY_FINISH_REASONS:
        raise GeminiError(ErrorCode.GEMINI_SAFETY_BLOCKED,
                          "The AI service declined to process this image (safety filter).")


# --- Service ---------------------------------------------------------------------------------

class GoogleGeminiService:
    def __init__(self, *, client: genai.Client, settings: Settings,
                 sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
                 rng: random.Random | None = None) -> None:
        self._client = client
        self._settings = settings
        self._semaphore = asyncio.Semaphore(settings.gemini_max_concurrency)
        self._sleep = sleep
        self._rng = rng or random.Random()  # noqa: S311 - jitter, not crypto

    @classmethod
    def from_settings(cls, settings: Settings) -> GoogleGeminiService:
        assert settings.gemini_api_key is not None
        return cls(client=genai.Client(api_key=settings.gemini_api_key.get_secret_value()),
                   settings=settings)

    async def aclose(self) -> None:
        await self._client.aio.aclose()

    # --- Public operations ---------------------------------------------------------------
    async def detect_objects(self, image: bytes, mime_type: str) -> DetectionResult:
        model = self._settings.gemini_vision_model
        if not model:
            raise GeminiError(ErrorCode.GEMINI_CONFIGURATION_ERROR,
                              "Object detection is not configured on this server.")
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=DETECTION_JSON_SCHEMA,
            http_options=types.HttpOptions(
                timeout=int(self._settings.gemini_detection_timeout_seconds * 1000)),
        )
        response = await self._call(
            model=model,
            contents=[types.Part.from_bytes(data=image, mime_type=mime_type), DETECTION_PROMPT],
            config=config,
        )
        if response.candidates[0].finish_reason == types.FinishReason.MAX_TOKENS:  # type: ignore[index]
            raise GeminiError(ErrorCode.GEMINI_INVALID_RESPONSE,
                              "The AI model's detection output was truncated.")
        return parse_detection_payload(response.text, model=model)

    async def edit_image(self, image: bytes, mime_type: str, *, prompt: str,
                         aspect_ratio: str | None) -> EditedImage:
        model = self._settings.gemini_image_edit_model
        if not model:
            raise GeminiError(ErrorCode.GEMINI_CONFIGURATION_ERROR,
                              "AI image editing is not configured on this server.")
        config = types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=aspect_ratio) if aspect_ratio else None,
            http_options=types.HttpOptions(
                timeout=int(self._settings.gemini_edit_timeout_seconds * 1000)),
        )
        response = await self._call(
            model=model,
            contents=[types.Part.from_bytes(data=image, mime_type=mime_type), prompt],
            config=config,
        )
        return self._extract_image(response, model)

    # --- Internals -----------------------------------------------------------------------
    @staticmethod
    def _extract_image(response: types.GenerateContentResponse, model: str) -> EditedImage:
        candidate = response.candidates[0]  # type: ignore[index]
        parts = (candidate.content.parts if candidate.content else None) or []
        image_parts = [
            p for p in parts
            if not p.thought and p.inline_data is not None and p.inline_data.data
            and (p.inline_data.mime_type or "").startswith("image/")
        ]
        if not image_parts:
            raise GeminiError(ErrorCode.GEMINI_INVALID_RESPONSE,
                              "The AI model did not return an edited image.")
        blob = image_parts[-1].inline_data
        assert blob is not None and blob.data is not None
        if len(blob.data) > MAX_EDIT_OUTPUT_BYTES:
            raise GeminiError(ErrorCode.GEMINI_INVALID_RESPONSE,
                              "The AI model returned an oversized image.")
        return EditedImage(data=blob.data, mime_type=blob.mime_type or "", model=model)

    async def _call(self, *, model: str, contents: list[Any],
                    config: types.GenerateContentConfig) -> types.GenerateContentResponse:
        attempts = self._settings.gemini_max_retries + 1
        for attempt in range(attempts):
            started = time.monotonic()
            try:
                response = await self._call_once(model=model, contents=contents, config=config)
                raise_if_blocked(response)
                logger.info("gemini_call_ok", extra={"gemini_model": model, "attempt": attempt,
                                                     "duration_ms": _ms_since(started)})
                return response
            except GeminiError as err:
                logger.warning("gemini_call_failed", extra={
                    "gemini_model": model, "attempt": attempt, "error_code": str(err.code),
                    "duration_ms": _ms_since(started)})
                if not err.retryable or attempt == attempts - 1:
                    raise
                delay = err.retry_after if err.retry_after is not None else backoff_delay(
                    attempt, base=1.0, cap=30.0, rng=self._rng)
                await self._sleep(delay)
        raise AssertionError("unreachable")  # pragma: no cover

    async def _call_once(self, *, model: str, contents: list[Any],
                         config: types.GenerateContentConfig) -> types.GenerateContentResponse:
        try:
            async with asyncio.timeout(self._settings.gemini_queue_timeout_seconds):
                await self._semaphore.acquire()
        except TimeoutError as exc:
            raise GeminiError(ErrorCode.GEMINI_RATE_LIMITED,
                              "The AI service is busy. Please retry later.") from exc
        try:
            return await self._client.aio.models.generate_content(
                model=model, contents=contents, config=config)
        except genai_errors.APIError as exc:
            raise classify_api_error(exc) from exc
        except httpx.TimeoutException as exc:
            raise GeminiError(ErrorCode.GEMINI_TIMEOUT, "The AI service timed out.",
                              retryable=True) from exc
        except httpx.TransportError as exc:
            raise GeminiError(ErrorCode.GEMINI_UNAVAILABLE,
                              "Could not reach the AI service.", retryable=True) from exc
        finally:
            self._semaphore.release()


def _ms_since(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
