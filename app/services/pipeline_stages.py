"""CPU-bound pipeline stages, executed in a process pool (never on the event loop).

Each stage is a top-level function taking only paths and plain values, so it pickles cleanly
across the process boundary. Errors are raised as (picklable) AppError.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from app.schemas.image import ProcessOptions
from app.services.image_processing_service import (
    EncodedImage,
    apply_adjustments,
    apply_filter,
    apply_transform,
    canonical_filter_name,
    check_output_size,
    compute_target_size,
    encode_for_model,
    encode_image,
    enhance_image,
    has_visible_transparency,
    load_normalized,
    resize_image,
)
from app.utils.filenames import OUTPUT_EXTENSIONS
from app.utils.image_validation import ImageInfo, validate_image_file


@dataclass(frozen=True, slots=True)
class Limits:
    max_pixels: int
    max_output_dimension: int
    default_quality: int


@dataclass(frozen=True, slots=True)
class ModelInput:
    data: bytes
    mime_type: str
    width: int
    height: int


@dataclass(slots=True)
class FinishResult:
    encoded: EncodedImage
    image_enhancement_completed: bool
    filter_applied: str | None = None
    warnings: list[dict[str, str]] = field(default_factory=list)


def init_worker(max_pixels: int) -> None:
    """Process-pool initializer: align Pillow's decompression-bomb guard with our limit."""
    Image.MAX_IMAGE_PIXELS = max_pixels


def stage_validate(path: str, original_filename: str | None, max_pixels: int) -> ImageInfo:
    return validate_image_file(Path(path), original_filename=original_filename,
                               max_pixels=max_pixels)


def stage_model_input(path: str, max_side: int, max_pixels: int) -> ModelInput:
    """Normalised, downscaled JPEG copy to send to Gemini."""
    image = load_normalized(Path(path), max_pixels=max_pixels)
    try:
        data, mime = encode_for_model(image, max_side=max_side)
        return ModelInput(data=data, mime_type=mime, width=image.width, height=image.height)
    finally:
        image.close()


def stage_finish(path: str, work_dir: str, options: dict[str, Any], default_format: str,
                 limits: Limits) -> FinishResult:
    """Normalise -> transform (rotate/flip) -> resize -> adjust -> filter -> enhance -> encode ->
    verify. Writes `output.<ext>` into the request's temp folder."""
    opts = ProcessOptions.model_validate(options)
    warnings: list[dict[str, str]] = []
    image = load_normalized(Path(path), max_pixels=limits.max_pixels)
    try:
        if opts.rotate or opts.flip_horizontal or opts.flip_vertical:
            image = apply_transform(image, rotate=opts.rotate,
                                    flip_horizontal=opts.flip_horizontal,
                                    flip_vertical=opts.flip_vertical)

        target = compute_target_size(image.width, image.height, opts.target_width,
                                     opts.target_height, opts.keep_aspect_ratio)
        check_output_size(target, max_dimension=limits.max_output_dimension,
                          max_pixels=limits.max_pixels)
        image = resize_image(image, target)

        if opts.brightness != 0 or opts.contrast != 0 or opts.saturation != 0:
            image = apply_adjustments(image, brightness=opts.brightness,
                                      contrast=opts.contrast,
                                      saturation=opts.saturation)

        applied_filter = None
        if opts.filter and opts.filter not in ("none", ""):
            image = apply_filter(image, opts.filter)
            applied_filter = canonical_filter_name(opts.filter)

        enhanced = False
        if opts.enhance_image:
            image = enhance_image(image)
            enhanced = True

        out_format = opts.output_format.value if opts.output_format else default_format
        if out_format == "PNG" and opts.quality is not None:
            warnings.append({"code": "QUALITY_IGNORED_FOR_PNG",
                             "message": "PNG output is lossless; the quality setting was "
                                        "ignored."})
        if out_format == "JPEG" and has_visible_transparency(image):
            warnings.append({"code": "TRANSPARENCY_REMOVED",
                             "message": "JPEG has no transparency; transparent areas were "
                                        "filled with white."})
        quality = opts.quality if opts.quality is not None else limits.default_quality
        dest = Path(work_dir) / f"output.{OUTPUT_EXTENSIONS[out_format]}"
        encoded = encode_image(image, dest, image_format=out_format, quality=quality)
        return FinishResult(encoded=encoded, image_enhancement_completed=enhanced,
                            filter_applied=applied_filter, warnings=warnings)
    finally:
        image.close()
