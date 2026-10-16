"""Deterministic, synchronous Pillow operations. Run these in worker processes, never on the
API event loop.

Every function returns a new image; inputs are not mutated.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageCms, ImageEnhance, ImageFilter, ImageOps

from app.core.errors import AppError, ErrorCode
from app.schemas.image import FILTER_ALIASES, VALID_FILTER_NAMES
from app.utils.filenames import MIME_TYPES
from app.utils.image_validation import open_image

logger = logging.getLogger(__name__)

# Aspect ratios accepted by Gemini image models' ImageConfig.aspect_ratio.
GEMINI_ASPECT_RATIOS = ("1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9")


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


def closest_aspect_ratio(size: tuple[int, int]) -> str:
    width, height = size
    ratio = width / height

    def distance(option: str) -> float:
        w, h = (int(x) for x in option.split(":"))
        return abs(ratio - w / h)

    return min(GEMINI_ASPECT_RATIOS, key=distance)


# --- Enhancement ------------------------------------------------------------------------------

def enhance_image(image: Image.Image) -> Image.Image:
    """Fixed, deterministic enhancement recipe (no AI):
    3x3 median denoise -> autocontrast (0.5% cutoff, tone-preserving) blended 50% with the
    original so it stays mild -> contrast x1.05 -> colour x1.05 -> unsharp mask
    (radius 1.5, 60%, threshold 3). Alpha is preserved."""
    alpha = image.getchannel("A") if image.mode == "RGBA" else None
    rgb = image.convert("RGB")
    rgb = rgb.filter(ImageFilter.MedianFilter(3))
    stretched = ImageOps.autocontrast(rgb, cutoff=0.5, preserve_tone=True)
    rgb = Image.blend(rgb, stretched, 0.5)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.05)
    rgb = ImageEnhance.Color(rgb).enhance(1.05)
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.5, percent=60, threshold=3))
    if alpha is not None:
        rgb.putalpha(alpha)
    return rgb


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


# --- Popular Filters, Adjustments & Transforms -----------------------------------------------

def apply_transform(image: Image.Image, *, rotate: int = 0,
                    flip_horizontal: bool = False,
                    flip_vertical: bool = False) -> Image.Image:
    """Rotate (0, 90, 180, 270 clockwise) and flip horizontally/vertically."""
    out = image
    rot = rotate % 360
    if rot == 90:
        out = out.transpose(Image.Transpose.ROTATE_270)
    elif rot == 180:
        out = out.transpose(Image.Transpose.ROTATE_180)
    elif rot == 270:
        out = out.transpose(Image.Transpose.ROTATE_90)
    if flip_horizontal:
        out = out.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if flip_vertical:
        out = out.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return out


def apply_adjustments(image: Image.Image, *, brightness: int = 0,
                      contrast: int = 0, saturation: int = 0) -> Image.Image:
    """Adjust brightness, contrast and saturation. Each value is in [-100, 100]."""
    out = image
    if brightness != 0:
        factor = max(0.0, 1.0 + (brightness / 100.0))
        out = ImageEnhance.Brightness(out).enhance(factor)
    if contrast != 0:
        factor = max(0.0, 1.0 + (contrast / 100.0))
        out = ImageEnhance.Contrast(out).enhance(factor)
    if saturation != 0:
        factor = max(0.0, 1.0 + (saturation / 100.0))
        out = ImageEnhance.Color(out).enhance(factor)
    return out


def canonical_filter_name(filter_name: str | None) -> str | None:
    """Resolve an alias (e.g. "bw") to its canonical name (e.g. "black_and_white"), so
    callers always report back one of a small, stable set of names. None for no filter."""
    if not filter_name or filter_name == "none":
        return None
    fn = filter_name.strip().lower()
    if fn in FILTER_ALIASES:
        return fn
    for canonical, aliases in FILTER_ALIASES.items():
        if fn in aliases:
            return canonical
    raise AppError(ErrorCode.VALIDATION_ERROR, f"Unknown filter {filter_name!r}.")


def apply_filter(image: Image.Image, filter_name: str | None) -> Image.Image:
    """Apply a photographic style preset: golden_hour, black_and_white, vintage, warm, cool.

    `filter_name` must already be validated (see `VALID_FILTER_NAMES`); an unrecognised name
    raises rather than silently passing the image through unchanged.
    """
    if not filter_name or filter_name == "none":
        return image

    fn = filter_name.strip().lower()
    if fn not in VALID_FILTER_NAMES:
        raise AppError(ErrorCode.VALIDATION_ERROR, f"Unknown filter {filter_name!r}.")
    alpha = image.getchannel("A") if image.mode == "RGBA" else None
    rgb = image.convert("RGB")

    if fn in ("black_and_white", *FILTER_ALIASES["black_and_white"]):
        gray = ImageOps.grayscale(rgb).convert("RGB")
        out = ImageEnhance.Contrast(gray).enhance(1.1)
    elif fn in ("golden_hour", *FILTER_ALIASES["golden_hour"]):
        r, g, b = rgb.split()
        r = r.point(lambda i: min(255, int(i * 1.15 + 12)))
        g = g.point(lambda i: min(255, int(i * 1.04 + 4)))
        b = b.point(lambda i: max(0, int(i * 0.88 - 6)))
        merged = Image.merge("RGB", (r, g, b))
        merged = ImageEnhance.Color(merged).enhance(1.15)
        out = ImageEnhance.Contrast(merged).enhance(1.08)
    elif fn in ("vintage", *FILTER_ALIASES["vintage"]):
        r, g, b = rgb.split()
        r = r.point(lambda i: min(255, int(i * 1.10 + 20)))
        g = g.point(lambda i: min(255, int(i * 1.02 + 12)))
        b = b.point(lambda i: min(255, max(15, int(i * 0.85 + 24))))
        merged = Image.merge("RGB", (r, g, b))
        merged = ImageEnhance.Contrast(merged).enhance(0.94)
        out = ImageEnhance.Color(merged).enhance(0.85)
    elif fn in ("warm", *FILTER_ALIASES["warm"]):
        r, g, b = rgb.split()
        r = r.point(lambda i: min(255, int(i * 1.08 + 8)))
        b = b.point(lambda i: max(0, int(i * 0.92)))
        out = Image.merge("RGB", (r, g, b))
    else:  # cool and its aliases
        r, g, b = rgb.split()
        r = r.point(lambda i: max(0, int(i * 0.92)))
        b = b.point(lambda i: min(255, int(i * 1.10 + 10)))
        merged = Image.merge("RGB", (r, g, b))
        out = ImageEnhance.Contrast(merged).enhance(1.05)

    if alpha is not None:
        out.putalpha(alpha)
    return out


def transform_box(box: Any, *, rotate: int = 0,
                  flip_horizontal: bool = False,
                  flip_vertical: bool = False) -> Any:
    """Transform a normalized bounding box to match rotated/flipped geometry."""
    x0, y0, x1, y1 = box.x_min, box.y_min, box.x_max, box.y_max
    rot = rotate % 360
    if rot == 90:
        x0, y0, x1, y1 = 1.0 - y1, x0, 1.0 - y0, x1
    elif rot == 180:
        x0, y0, x1, y1 = 1.0 - x1, 1.0 - y1, 1.0 - x0, 1.0 - y0
    elif rot == 270:
        x0, y0, x1, y1 = y0, 1.0 - x1, y1, 1.0 - x0

    if flip_horizontal:
        x0, x1 = 1.0 - x1, 1.0 - x0
    if flip_vertical:
        y0, y1 = 1.0 - y1, 1.0 - y0

    nx_min = max(0.0, min(1.0, min(x0, x1)))
    ny_min = max(0.0, min(1.0, min(y0, y1)))
    nx_max = max(0.0, min(1.0, max(x0, x1)))
    ny_max = max(0.0, min(1.0, max(y0, y1)))

    return type(box)(x_min=nx_min, y_min=ny_min, x_max=nx_max, y_max=ny_max)
