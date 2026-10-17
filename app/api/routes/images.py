from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import ValidationError

from app.api.deps import AppResources, client_ip, get_request_id, get_resources
from app.api.errors import validation_details
from app.core.errors import AppError, ErrorCode, retry_after_error
from app.schemas.errors import ErrorResponse
from app.schemas.image import (
    BoundingBox,
    CapabilitiesResponse,
    DetectedObjectOut,
    NormalizedBoundingBox,
    OriginalImage,
    OutputFormat,
    ProcessedImage,
    ProcessingFlags,
    ProcessingWarning,
    ProcessOptions,
    ProcessResponse,
)
from app.services.processing_service import ProcessResult, to_data_url

router = APIRouter(prefix="/api/v1", tags=["images"])

_ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorResponse} for code in (413, 415, 422, 429, 500, 502, 503, 504)
}


def _response(result: ProcessResult, request_id: str) -> ProcessResponse:
    detected = []
    for det in result.detections:
        box = BoundingBox(x_min=det.box[0], y_min=det.box[1], x_max=det.box[2],
                          y_max=det.box[3]) if det.box else None
        norm = NormalizedBoundingBox(
            x_min=det.normalized.x_min, y_min=det.normalized.y_min,
            x_max=det.normalized.x_max, y_max=det.normalized.y_max,
        ) if det.normalized else None
        detected.append(DetectedObjectOut(label=det.label, category=det.category,
                                          description=det.description, bounding_box=box,
                                          normalized_bounding_box=norm,
                                          confidence=det.confidence))
    original = result.original
    return ProcessResponse(
        request_id=request_id,
        image=ProcessedImage(
            data_url=to_data_url(result.data, result.mime_type),
            download_filename=result.download_filename, format=result.format,
            width=result.width, height=result.height, size_bytes=len(result.data),
            mime_type=result.mime_type),
        original=OriginalImage(filename=result.original_filename, format=original.format,
                               width=original.width, height=original.height,
                               size_bytes=result.original_size_bytes,
                               mime_type=original.mime_type),
        main_subject=result.main_subject,
        detected_objects=detected,
        processing=ProcessingFlags(
            object_detection_completed=result.object_detection_completed),
        warnings=[ProcessingWarning(**w) for w in result.warnings],
        ai_models_used=result.ai_models_used,
        duration_ms=result.duration_ms,
    )


@router.post("/images/process", response_model=ProcessResponse,
             summary="Upload an image and get the processed result", responses=_ERRORS)
async def process_image(
    request: Request,
    image: Annotated[UploadFile, File(description="JPEG, PNG or WEBP image.")],
    target_width: Annotated[int | None, Form(description="Output width in px.")] = None,
    target_height: Annotated[int | None, Form(description="Output height in px.")] = None,
    keep_aspect_ratio: Annotated[bool, Form(
        description="Fit within target_width x target_height without cropping.")] = True,
    output_format: Annotated[str | None, Form(
        description="JPEG, PNG or WEBP. Defaults to the input format.")] = None,
    quality: Annotated[int | None, Form(description="1-100 (JPEG/WEBP).")] = None,
    detect_objects: Annotated[bool, Form(description="Run Gemini object detection.")] = False,
    resources: AppResources = Depends(get_resources),
    request_id: str = Depends(get_request_id),
) -> ProcessResponse:
    try:
        options = ProcessOptions(
            target_width=target_width, target_height=target_height,
            keep_aspect_ratio=keep_aspect_ratio, output_format=output_format, quality=quality,
            detect_objects=detect_objects,
        )
    except ValidationError as exc:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Invalid processing options.",
                       details=validation_details(exc.errors())) from exc

    ip = client_ip(request)
    wait = resources.ip_rate_limiter.hit(ip)
    if wait:
        raise retry_after_error(ErrorCode.RATE_LIMITED, "Too many requests. Please slow down.",
                                wait)
    with resources.admission.admit(ip):
        result = await resources.processor.process(
            request_id=request_id, upload=image.file, filename=image.filename, options=options)
    return _response(result, request_id)


@router.get("/capabilities", response_model=CapabilitiesResponse,
            summary="Which features and limits this server supports")
async def capabilities(resources: AppResources = Depends(get_resources)) -> CapabilitiesResponse:
    s = resources.settings
    return CapabilitiesResponse(
        object_detection=s.detection_enabled and resources.gemini is not None,
        vision_model=s.gemini_vision_model if s.detection_enabled else None,
        accepted_formats=["JPEG", "PNG", "WEBP"],
        output_formats=[f.value for f in OutputFormat],
        max_upload_bytes=s.max_upload_bytes, max_image_pixels=s.max_image_pixels,
        max_output_dimension=s.max_output_dimension, default_quality=s.default_quality,
    )
