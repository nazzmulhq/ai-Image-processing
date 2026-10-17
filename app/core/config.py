"""Application settings, loaded from environment variables (and `.env` in development)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _default_cpu_workers() -> int:
    return max(1, min(8, os.cpu_count() or 2))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- General -----------------------------------------------------------------------------
    app_name: str = "AI Image Processing"
    log_level: str = "INFO"
    # Extra origins allowed to call the API from a browser (the built-in UI is same-origin).
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    serve_frontend: bool = True

    # Private per-request scratch space. Nothing is kept after a response is sent.
    temp_dir: Path = Path("tmp/imgproc")

    # --- Gemini ------------------------------------------------------------------------------
    gemini_api_key: SecretStr | None = None
    gemini_vision_model: str | None = "gemini-3.8-flash"
    gemini_detection_timeout_seconds: float = Field(60, gt=0)
    gemini_max_retries: int = Field(3, ge=0, le=10)
    # Max simultaneous Gemini calls from this process (protects your quota).
    gemini_max_concurrency: int = Field(4, ge=1)
    gemini_queue_timeout_seconds: float = Field(30, gt=0)
    gemini_detection_max_side: int = Field(1536, ge=256, le=4096)

    # --- Image limits ------------------------------------------------------------------------
    max_upload_bytes: int = Field(20 * 1024 * 1024, ge=1024)
    max_image_pixels: int = Field(40_000_000, ge=1)
    max_output_dimension: int = Field(8192, ge=16, le=16383)
    # The processed image is returned inline (base64) and must fit in the response.
    max_output_bytes: int = Field(15 * 1024 * 1024, ge=1024)
    default_quality: int = Field(85, ge=1, le=100)

    # --- Concurrency / backpressure (per server process) -----------------------------------
    # Processes in the Pillow pool (true CPU parallelism, isolated from the event loop).
    cpu_workers: int = Field(default_factory=_default_cpu_workers, ge=1)
    # Requests processed at once; extra requests get 503 + Retry-After instead of hanging.
    max_concurrent_requests: int = Field(16, ge=1)
    max_concurrent_per_ip: int = Field(3, ge=1)
    rate_limit_ip_per_minute: int = Field(30, ge=1)
    # Hard limit for one request's processing (Gemini calls included).
    request_timeout_seconds: float = Field(150, gt=0)
    # Leftover temp folders (e.g. after a crash) older than this are removed.
    temp_max_age_seconds: int = Field(900, ge=60)
    temp_sweep_interval_seconds: int = Field(300, ge=10)

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("gemini_vision_model", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.get_secret_value())

    @property
    def detection_enabled(self) -> bool:
        return self.gemini_configured and bool(self.gemini_vision_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()
