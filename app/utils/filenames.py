"""Server-generated identifiers and safe display names. User-supplied names never touch disk."""

from __future__ import annotations

import re
import unicodedata
import uuid

OUTPUT_EXTENSIONS: dict[str, str] = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
MIME_TYPES: dict[str, str] = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}

HEX_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_UNSAFE_CHARS_RE = re.compile(r"[^\w .()\-]+", re.UNICODE)


def new_id() -> str:
    """A random 128-bit identifier (uuid4, 32 lowercase hex chars)."""
    return uuid.uuid4().hex


def extension_of(filename: str | None) -> str | None:
    if not filename:
        return None
    base = re.split(r"[\\/]", filename)[-1]
    if "." not in base.strip("."):
        return None
    return base.rsplit(".", 1)[-1].lower() or None


def sanitize_original_filename(filename: str | None, max_length: int = 200) -> str | None:
    """Return a display-safe version of a client filename (metadata only, never a path)."""
    if not filename:
        return None
    name = re.split(r"[\\/]", filename)[-1]
    name = unicodedata.normalize("NFKC", name)
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
    name = _UNSAFE_CHARS_RE.sub("_", name).strip().lstrip(".")
    if not name:
        return None
    if len(name) > max_length:
        stem, dot, ext = name.rpartition(".")
        if dot and 0 < len(ext) <= 10:
            name = stem[: max_length - len(ext) - 1] + "." + ext
        else:
            name = name[:max_length]
    return name


def download_filename(original: str | None, image_format: str) -> str:
    """Suggested name for saving the processed image, e.g. `cat-processed.webp`."""
    safe = sanitize_original_filename(original, max_length=120) or "image"
    stem = safe.rsplit(".", 1)[0] if "." in safe else safe
    return f"{stem or 'image'}-processed.{OUTPUT_EXTENSIONS[image_format]}"
