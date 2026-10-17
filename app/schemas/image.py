from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    @field_validator("output_format", mode="before")
    @classmethod
    def _normalize_format(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip().upper()
            if not value:
                return None
            return "JPEG" if value == "JPG" else value
        return value


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
    warnings: list[ProcessingWarning]
    ai_models_used: list[str]
    duration_ms: int


class CapabilitiesResponse(BaseModel):
    object_detection: bool
    vision_model: str | None
    accepted_formats: list[str]
    output_formats: list[str]
    max_upload_bytes: int
    max_image_pixels: int
    max_output_dimension: int
    default_quality: int
