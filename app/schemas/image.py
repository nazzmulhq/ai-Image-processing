from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

VALID_ROTATIONS = (0, 90, 180, 270)

# Canonical filter name -> accepted aliases. Schema validation and
# `image_processing_service.apply_filter` both key off this, so an unrecognised name is
# rejected up front with a 422 instead of silently doing nothing.
FILTER_ALIASES: dict[str, tuple[str, ...]] = {
    "black_and_white": ("bw", "monochrome"),
    "golden_hour": ("sunset", "golden"),
    "vintage": ("old_film", "retro"),
    "warm": ("cozy",),
    "cool": ("cold", "cyber"),
}
VALID_FILTER_NAMES: frozenset[str] = frozenset(
    {"none", *FILTER_ALIASES, *(a for aliases in FILTER_ALIASES.values() for a in aliases)}
)

REMOVE_BACKGROUND_PROMPT = (
    "Remove the background from this image. Keep the main subject exactly as it is - same "
    "pose, proportions, colours and details - and place it on a plain, uniform pure white "
    "(#FFFFFF) background. Do not add any new objects, text, borders or shadows."
)


class OutputFormat(StrEnum):
    JPEG = "JPEG"
    PNG = "PNG"
    WEBP = "WEBP"


class ProcessOptions(BaseModel):
    """Processing options sent as multipart form fields alongside the image."""

    model_config = ConfigDict(extra="forbid")

    target_width: int | None = Field(None, ge=1, le=16383)
    target_height: int | None = Field(None, ge=1, le=16383)
    keep_aspect_ratio: bool = True
    output_format: OutputFormat | None = None
    quality: int | None = Field(None, ge=1, le=100)
    detect_objects: bool = False
    enhance_image: bool = False
    ai_edit_prompt: str | None = Field(None, min_length=1, max_length=2000)
    remove_background: bool = False
    filter: str | None = Field(
        None, description="Preset filter: golden_hour, black_and_white, vintage, warm, cool.")
    brightness: int = Field(0, ge=-100, le=100)
    contrast: int = Field(0, ge=-100, le=100)
    saturation: int = Field(0, ge=-100, le=100)
    rotate: int = Field(0, ge=0, le=360)
    flip_horizontal: bool = False
    flip_vertical: bool = False

    @field_validator("output_format", mode="before")
    @classmethod
    def _normalize_format(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip().upper()
            if not value:
                return None
            return "JPEG" if value == "JPG" else value
        return value

    @field_validator("rotate")
    @classmethod
    def _check_rotate(cls, value: int) -> int:
        if value not in VALID_ROTATIONS:
            raise ValueError(f"rotate must be one of {VALID_ROTATIONS}, got {value}.")
        return value

    @field_validator("filter", mode="before")
    @classmethod
    def _check_filter(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = value.strip().lower()
        if not value:
            return None
        if value not in VALID_FILTER_NAMES:
            raise ValueError(f"Unknown filter {value!r}; expected one of "
                             f"{sorted(VALID_FILTER_NAMES)}.")
        return value

    @field_validator("ai_edit_prompt", mode="before")
    @classmethod
    def _strip_prompt(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @model_validator(mode="after")
    def _check_combinations(self) -> ProcessOptions:
        if self.ai_edit_prompt and self.remove_background:
            raise ValueError("Use either ai_edit_prompt or remove_background, not both.")
        return self

    @property
    def wants_ai_edit(self) -> bool:
        return bool(self.ai_edit_prompt) or self.remove_background

    @property
    def effective_edit_prompt(self) -> str | None:
        if self.remove_background:
            return REMOVE_BACKGROUND_PROMPT
        return self.ai_edit_prompt


class ProcessedImage(BaseModel):
    data_url: str = Field(description="The processed image as a base64 `data:` URL.")
    download_filename: str
    format: str
    width: int
    height: int
    size_bytes: int
    mime_type: str


class OriginalImage(BaseModel):
    filename: str | None
    format: str
    width: int
    height: int
    size_bytes: int
    mime_type: str


class BoundingBox(BaseModel):
    """Pixel coordinates in the processed image."""

    x_min: int
    y_min: int
    x_max: int
    y_max: int


class NormalizedBoundingBox(BaseModel):
    """The same box as fractions (0..1) of the processed image's width and height."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float


class DetectedObjectOut(BaseModel):
    label: str
    category: str | None = None
    description: str | None = None
    bounding_box: BoundingBox | None = None
    normalized_bounding_box: NormalizedBoundingBox | None = None
    # Gemini does not return calibrated confidence scores, so this is always null.
    confidence: float | None = None


class ProcessingFlags(BaseModel):
    object_detection_completed: bool
    image_enhancement_completed: bool
    ai_edit_completed: bool


class ProcessingWarning(BaseModel):
    code: str
    message: str


class ProcessResponse(BaseModel):
    success: Literal[True] = True
    request_id: str
    image: ProcessedImage
    original: OriginalImage
    main_subject: str | None
    detected_objects: list[DetectedObjectOut]
    processing: ProcessingFlags
    filter_applied: str | None = None
    warnings: list[ProcessingWarning]
    ai_models_used: list[str]
    duration_ms: int


class CapabilitiesResponse(BaseModel):
    object_detection: bool
    ai_edit: bool
    vision_model: str | None
    image_edit_model: str | None
    accepted_formats: list[str]
    output_formats: list[str]
    max_upload_bytes: int
    max_image_pixels: int
    max_output_dimension: int
    default_quality: int
