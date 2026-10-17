"""Stateless request pipeline. Nothing is stored: the upload lives in the request's private
temp folder only while it is processed, the result is returned inline, and the folder is
deleted in `finally` on every outcome.

Order: stream upload -> validate -> ([Gemini detect] || resize/encode) -> verify -> respond.
Detection runs in parallel with the Pillow work; resizing never crops, so normalised boxes
map exactly onto the final pixels.
"""

from __future__ import annotations

import asyncio
import base64
import functools
import logging
import math
import time
from collections.abc import Callable
from concurrent.futures import Executor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, TypeVar

import anyio

from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.schemas.image import ProcessOptions
from app.services.gemini_service import (
    DetectionResult,
    GeminiError,
    GeminiService,
    NormalizedBox,
)
from app.services.pipeline_stages import (
    FinishResult,
    Limits,
    ModelInput,
    stage_finish,
    stage_model_input,
    stage_validate,
)
from app.services.workspace import TempWorkspace, copy_upload
from app.utils.filenames import download_filename, sanitize_original_filename
from app.utils.image_validation import ImageInfo

logger = logging.getLogger(__name__)
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PixelDetection:
    label: str
    category: str | None
    description: str | None
    box: tuple[int, int, int, int] | None
    normalized: NormalizedBox | None
    confidence: float | None


@dataclass
class ProcessResult:
    data: bytes
    format: str
    mime_type: str
    width: int
    height: int
    download_filename: str
    original: ImageInfo
    original_filename: str | None
    original_size_bytes: int
    main_subject: str | None
    detections: list[PixelDetection]
    object_detection_completed: bool
    ai_models_used: list[str]
    warnings: list[dict[str, str]] = field(default_factory=list)
    duration_ms: int = 0


def to_pixel_box(box: NormalizedBox, width: int, height: int) -> tuple[int, int, int, int]:
    x_min = min(width - 1, max(0, math.floor(box.x_min * width)))
    y_min = min(height - 1, max(0, math.floor(box.y_min * height)))
    x_max = max(x_min + 1, min(width, math.ceil(box.x_max * width)))
    y_max = max(y_min + 1, min(height, math.ceil(box.y_max * height)))
    return x_min, y_min, x_max, y_max


def _first_error(group: BaseExceptionGroup) -> BaseException:  # type: ignore[type-arg]
    leaves: list[BaseException] = []

    def walk(exc: BaseException) -> None:
        if isinstance(exc, BaseExceptionGroup):
            for inner in exc.exceptions:
                walk(inner)
        else:
            leaves.append(exc)

    walk(group)
    return next((e for e in leaves if isinstance(e, AppError)), leaves[0])


class ImageProcessor:
    def __init__(self, *, settings: Settings, executor: Executor,
                 gemini: GeminiService | None) -> None:
        self.settings = settings
        self._executor = executor
        self._gemini = gemini
        self._limits = Limits(max_pixels=settings.max_image_pixels,
                              max_output_dimension=settings.max_output_dimension,
                              default_quality=settings.default_quality)
        # Request ids currently being processed by this process; the temp sweeper skips them.
        self.active_requests: set[str] = set()

    async def _cpu(self, fn: Callable[..., T], *args: Any) -> T:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, functools.partial(fn, *args))

    def check_features(self, options: ProcessOptions) -> None:
        if options.detect_objects and not (self.settings.detection_enabled and self._gemini):
            raise AppError(ErrorCode.FEATURE_NOT_CONFIGURED,
                           "Object detection is not configured on this server "
                           "(set GEMINI_API_KEY).")
        max_dim = self.settings.max_output_dimension
        for name, value in (("target_width", options.target_width),
                            ("target_height", options.target_height)):
            if value is not None and value > max_dim:
                raise AppError(ErrorCode.VALIDATION_ERROR,
                               f"{name} must be at most {max_dim} pixels.")

    async def process(self, *, request_id: str, upload: BinaryIO, filename: str | None,
                      options: ProcessOptions) -> ProcessResult:
        self.check_features(options)
        started = time.monotonic()
        workspace = TempWorkspace(self.settings.temp_dir, request_id)
        await anyio.to_thread.run_sync(workspace.create)
        self.active_requests.add(request_id)
        try:
            size, _sha = await anyio.to_thread.run_sync(
                copy_upload, upload, workspace.upload_path, self.settings.max_upload_bytes)
            info = await self._cpu(stage_validate, str(workspace.upload_path), filename,
                                   self.settings.max_image_pixels)
            try:
                async with asyncio.timeout(self.settings.request_timeout_seconds):
                    result = await self._pipeline(workspace, info, options)
            except TimeoutError as exc:
                raise AppError(ErrorCode.PROCESSING_TIMEOUT,
                               "Processing took too long and was stopped.") from exc
            result.original = info
            result.original_filename = sanitize_original_filename(filename)
            result.original_size_bytes = size
            result.download_filename = download_filename(filename, result.format)
            result.duration_ms = int((time.monotonic() - started) * 1000)
            return result
        finally:
            self.active_requests.discard(request_id)
            await anyio.to_thread.run_sync(workspace.cleanup)

    async def _pipeline(self, workspace: TempWorkspace, info: ImageInfo,
                        options: ProcessOptions) -> ProcessResult:
        settings = self.settings
        warnings: list[dict[str, str]] = []
        models: list[str] = []
        source = workspace.upload_path

        # Detection (Gemini) and local processing (Pillow) run concurrently.
        try:
            async with asyncio.TaskGroup() as group:
                detect_task = (group.create_task(self._detect(source, warnings))
                               if options.detect_objects else None)
                finish_task = group.create_task(self._cpu(
                    stage_finish, str(source), str(workspace.path),
                    options.model_dump(mode="json"), info.format, self._limits))
        except BaseExceptionGroup as group_error:
            raise _first_error(group_error) from None

        detection = detect_task.result() if detect_task else None
        finish: FinishResult = finish_task.result()
        warnings.extend(finish.warnings)
        if detection is not None:
            models.append(detection.model)

        encoded = finish.encoded
        if encoded.size_bytes > settings.max_output_bytes:
            raise AppError(ErrorCode.OUTPUT_TOO_LARGE,
                           f"The processed image is {encoded.size_bytes:,} bytes, above the "
                           f"{settings.max_output_bytes:,}-byte response limit. Request a "
                           "smaller size or JPEG/WEBP output.")
        data = await anyio.to_thread.run_sync(encoded.path.read_bytes)

        detections = []
        for obj in detection.objects if detection else []:
            box = to_pixel_box(obj.box, encoded.width, encoded.height) if obj.box else None
            detections.append(PixelDetection(label=obj.label, category=obj.category,
                                             description=obj.description, box=box,
                                             normalized=obj.box, confidence=obj.confidence))
        return ProcessResult(
            data=data, format=encoded.format, mime_type=encoded.mime_type,
            width=encoded.width, height=encoded.height, download_filename="",
            original=info, original_filename=None, original_size_bytes=0,
            main_subject=detection.main_subject if detection else None,
            detections=detections,
            object_detection_completed=detection is not None,
            ai_models_used=models, warnings=warnings,
        )

    async def _detect(self, source: Path, warnings: list[dict[str, str]]
                      ) -> DetectionResult | None:
        """Never raises for Gemini failures: the image is still returned, with a warning
        and object_detection_completed=false."""
        assert self._gemini is not None
        model_input: ModelInput = await self._cpu(
            stage_model_input, str(source), self.settings.gemini_detection_max_side,
            self.settings.max_image_pixels)
        try:
            detection = await self._gemini.detect_objects(model_input.data,
                                                          model_input.mime_type)
        except GeminiError as err:
            logger.warning("object_detection_failed", extra={"error_code": str(err.code)})
            warnings.append({"code": "OBJECT_DETECTION_FAILED",
                             "message": f"Object detection failed: {err.message}"})
            return None
        if detection.invalid_boxes:
            warnings.append({"code": "INVALID_BOUNDING_BOXES_OMITTED",
                             "message": f"{detection.invalid_boxes} bounding box(es) returned "
                                        "by the model were invalid and were omitted."})
        if detection.truncated_objects:
            warnings.append({"code": "DETECTIONS_TRUNCATED",
                             "message": f"{detection.truncated_objects} additional detected "
                                        "object(s) were omitted."})
        return detection


def to_data_url(data: bytes, mime_type: str) -> str:
    return f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"
