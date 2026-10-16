"""Content-based image validation: magic bytes, Pillow parsing, pixel limits, truncation.

The file content is authoritative; the client's filename and Content-Type are not trusted.
"""

from __future__ import annotations

import struct
import warnings
import zlib
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.core.errors import AppError, ErrorCode
from app.utils.filenames import MIME_TYPES, extension_of

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "jpe", "jfif", "png", "webp"}
# Pillow reports multi-picture JPEGs (common from phone cameras) as MPO; frame 0 is the photo.
_PILLOW_FORMATS = {"JPEG": {"JPEG", "MPO"}, "PNG": {"PNG"}, "WEBP": {"WEBP"}}
_DECODE_ERRORS = (UnidentifiedImageError, OSError, SyntaxError, ValueError, struct.error,
                  EOFError, IndexError, zlib.error)


@dataclass(frozen=True, slots=True)
class ImageInfo:
    format: str  # JPEG | PNG | WEBP
    mime_type: str
    width: int
    height: int


def sniff_format(head: bytes) -> str | None:
    """Identify the format from magic bytes."""
    if head.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "WEBP"
    return None


def _unsupported() -> AppError:
    return AppError(ErrorCode.UNSUPPORTED_FILE_TYPE,
                    "Unsupported file type. Upload a JPEG, PNG or WEBP image.")


def _corrupted() -> AppError:
    return AppError(ErrorCode.CORRUPTED_IMAGE, "The image file is corrupted or truncated.")


def _too_large(max_pixels: int) -> AppError:
    return AppError(ErrorCode.IMAGE_TOO_LARGE,
                    f"Image has too many pixels (maximum is {max_pixels:,}).",
                    details={"max_pixels": max_pixels})


def check_filename_extension(original_filename: str | None) -> None:
    ext = extension_of(original_filename)
    if ext is not None and ext not in ALLOWED_EXTENSIONS:
        raise _unsupported()


def open_image(path: Path, *, max_pixels: int, reduced_decode: bool = False) -> Image.Image:
    """Open, verify and fully decode an image, enforcing type and size limits.

    Returns a loaded `Image.Image` (frame 0). `reduced_decode=True` lets JPEG decode at
    reduced scale (still walks the whole bitstream) to validate cheaply.
    """
    with path.open("rb") as fh:
        head = fh.read(16)
    sniffed = sniff_format(head)
    if sniffed is None:
        raise _unsupported()

    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            # Header-only parse: dimensions are known before any pixel data is decoded.
            with Image.open(path) as probe:
                if probe.format not in _PILLOW_FORMATS[sniffed]:
                    raise _unsupported()
                width, height = probe.size
                if width < 1 or height < 1:
                    raise _corrupted()
                if width * height > max_pixels:
                    raise _too_large(max_pixels)
                if probe.format != "MPO" and getattr(probe, "n_frames", 1) > 1:
                    raise AppError(ErrorCode.ANIMATED_IMAGE_UNSUPPORTED,
                                   "Animated images are not supported.")
                probe.verify()

            image = Image.open(path)  # verify() leaves the image unusable; reopen.
            try:
                if reduced_decode and image.format in ("JPEG", "MPO"):
                    image.draft(image.mode, (max(1, width // 8), max(1, height // 8)))
                image.load()
            except BaseException:
                image.close()
                raise
            return image
        except AppError:
            raise
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise _too_large(max_pixels) from exc
        except _DECODE_ERRORS as exc:
            raise _corrupted() from exc


def validate_image_file(path: Path, *, original_filename: str | None,
                        max_pixels: int) -> ImageInfo:
    """Validate an uploaded file and return its real format and dimensions."""
    check_filename_extension(original_filename)
    with open_image(path, max_pixels=max_pixels, reduced_decode=True) as image:
        fmt = normalized_format(image)
    # Read the true dimensions from the header (draft mode shrinks image.size).
    with Image.open(path) as header:
        width, height = header.size
    return ImageInfo(format=fmt, mime_type=MIME_TYPES[fmt], width=width, height=height)


def normalized_format(image: Image.Image) -> str:
    return "JPEG" if image.format in ("JPEG", "MPO") else str(image.format)
