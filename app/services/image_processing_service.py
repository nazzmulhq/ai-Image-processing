"""Deterministic, synchronous Pillow operations. Run these in worker processes, never on the
API event loop.

Every function returns a new image; inputs are not mutated.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageCms, ImageOps

from app.core.errors import AppError, ErrorCode
from app.utils.filenames import MIME_TYPES
from app.utils.image_validation import open_image

logger = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class EncodedImage:
    path: Path
    format: str
    mime_type: str
    width: int
    height: int
    size_bytes: int


# --- Loading & normalisation -----------------------------------------------------------------

def load_normalized(path: Path, *, max_pixels: int) -> Image.Image:
    """Open + fully decode a validated file, apply EXIF orientation, convert to sRGB RGB/RGBA
    and drop all metadata (EXIF, GPS, XMP, ICC, comments)."""
    with open_image(path, max_pixels=max_pixels) as image:
        return normalize_image(image)


def normalize_image(image: Image.Image) -> Image.Image:
    oriented = ImageOps.exif_transpose(image)  # returns a copy with orientation applied
    oriented = _to_srgb(oriented)
    oriented = _normalize_mode(oriented)
    # Rebuild from pixels only so no metadata (info/exif/icc) survives.
    clean = Image.new(oriented.mode, oriented.size)
    clean.paste(oriented)
    return clean


def _to_srgb(image: Image.Image) -> Image.Image:
    icc = image.info.get("icc_profile")
    if not icc or image.mode not in ("RGB", "RGBA", "CMYK"):
        return image
    try:
        source = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        target = ImageCms.createProfile("sRGB")
        output_mode = "RGBA" if image.mode == "RGBA" else "RGB"
        converted = ImageCms.profileToProfile(image, source, target, outputMode=output_mode)
        return converted if converted is not None else image
    except (ImageCms.PyCMSError, OSError, ValueError):
        logger.warning("icc_conversion_failed")
        return image


def _has_alpha(image: Image.Image) -> bool:
    return image.mode in ("RGBA", "LA", "PA", "La", "RGBa") or (
        image.mode == "P" and "transparency" in image.info
    )


def _normalize_mode(image: Image.Image) -> Image.Image:
    if image.mode in ("RGB", "RGBA"):
        return image
    if image.mode in ("I;16", "I;16B", "I;16L", "I;16N", "I"):
        # 16/32-bit grayscale: scale into 8-bit instead of clipping to white.
        scaled = image.convert("I").point(lambda v: v * (1 / 256))
        return scaled.convert("L").convert("RGB")
    if image.mode == "F":
        return image.convert("L").convert("RGB")
    return image.convert("RGBA" if _has_alpha(image) else "RGB")


# --- Geometry ---------------------------------------------------------------------------------

def compute_target_size(width: int, height: int, target_width: int | None,
                        target_height: int | None, keep_aspect_ratio: bool) -> tuple[int, int]:
    """Return the output size. With keep_aspect_ratio the image fits inside the requested
    box (never cropped); otherwise it is scaled to exactly the requested dimensions."""
    if not target_width and not target_height:
        return width, height
    if not keep_aspect_ratio:
        return target_width or width, target_height or height
    if target_width and target_height:
        scale = min(target_width / width, target_height / height)
    elif target_width:
        scale = target_width / width
    else:
        scale = target_height / height  # type: ignore[operator]
    return max(1, round(width * scale)), max(1, round(height * scale))


def check_output_size(size: tuple[int, int], *, max_dimension: int, max_pixels: int) -> None:
    width, height = size
    if width > max_dimension or height > max_dimension or width * height > max_pixels:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            f"Requested output size {width}x{height} exceeds the limits "
            f"(max side {max_dimension}px, max {max_pixels:,} pixels).",
        )


def resize_image(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    if image.size == size:
        return image
    return image.resize(size, Image.Resampling.LANCZOS, reducing_gap=3.0)


# --- Encoding ---------------------------------------------------------------------------------

def has_visible_transparency(image: Image.Image) -> bool:
    if image.mode != "RGBA":
        return False
    low, _high = image.getchannel("A").getextrema()
    return low < 255


def flatten_alpha(image: Image.Image, background: tuple[int, int, int] = (255, 255, 255)
                  ) -> Image.Image:
    if image.mode != "RGBA":
        return image.convert("RGB")
    base = Image.new("RGB", image.size, background)
    base.paste(image, mask=image.getchannel("A"))
    return base


def encode_image(image: Image.Image, dest: Path, *, image_format: str,
                 quality: int) -> EncodedImage:
    """Encode to `dest` without any metadata and verify the written file."""
    if image_format == "JPEG":
        out = flatten_alpha(image)
        out.save(dest, "JPEG", quality=quality, optimize=True, progressive=True)
    elif image_format == "WEBP":
        image.save(dest, "WEBP", quality=quality, method=4)
    elif image_format == "PNG":
        image.save(dest, "PNG", compress_level=7)
    else:  # pragma: no cover - guarded by schema validation
        raise AppError(ErrorCode.VALIDATION_ERROR, f"Unsupported output format {image_format}.")
    validate_output(dest, image_format=image_format, size=image.size)
    return EncodedImage(
        path=dest,
        format=image_format,
        mime_type=MIME_TYPES[image_format],
        width=image.width,
        height=image.height,
        size_bytes=dest.stat().st_size,
    )


def validate_output(path: Path, *, image_format: str, size: tuple[int, int]) -> None:
    """Re-open the encoded file and confirm it decodes with the expected format and size."""
    try:
        with Image.open(path) as check:
            fmt, actual_size = check.format, check.size
            check.verify()
        with Image.open(path) as check:
            check.load()
    except Exception as exc:
        raise AppError(ErrorCode.PROCESSING_FAILED,
                       "The processed image failed validation.") from exc
    if fmt != image_format or actual_size != size:
        raise AppError(ErrorCode.PROCESSING_FAILED, "The processed image failed validation.")


def encode_for_model(image: Image.Image, *, max_side: int, quality: int = 90
                     ) -> tuple[bytes, str]:
    """A downscaled JPEG copy to send to Gemini (keeps requests small and fast). Normalised
    bounding-box coordinates are unaffected by uniform scaling."""
    copy = flatten_alpha(image)
    copy.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    copy.save(buffer, "JPEG", quality=quality)
    return buffer.getvalue(), "image/jpeg"
