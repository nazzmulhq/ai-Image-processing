"""Private per-request temp folders and the sweeper that removes crash leftovers.

Every request gets `{temp_dir}/{request_id}/` (mode 700). It is deleted in a `finally`
block when the request ends, whatever the outcome. Nothing else is ever written to disk.
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import os
import shutil
import time
from collections.abc import Container
from pathlib import Path
from typing import BinaryIO

from app.core.errors import AppError, ErrorCode
from app.utils.filenames import HEX_ID_RE

logger = logging.getLogger(__name__)

_COPY_CHUNK = 1024 * 1024


class TempWorkspace:
    def __init__(self, temp_root: Path, request_id: str) -> None:
        if not HEX_ID_RE.fullmatch(request_id):
            raise ValueError("invalid request id")
        self.request_id = request_id
        self.path = temp_root / request_id

    @property
    def upload_path(self) -> Path:
        return self.path / "upload"

    def create(self) -> TempWorkspace:
        self.path.mkdir(mode=0o700)  # fails if it exists: request ids are unique
        return self

    def exists(self) -> bool:
        return self.path.is_dir()

    def cleanup(self) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


def ensure_temp_root(temp_root: Path) -> None:
    temp_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with contextlib.suppress(OSError):  # tighten a pre-existing directory
        temp_root.chmod(0o700)


def copy_upload(src: BinaryIO, dest: Path, max_bytes: int) -> tuple[int, str]:
    """Stream an upload into the request's temp folder in chunks (never fully in memory),
    enforcing the size limit and hashing as we go. Returns (size, sha256)."""
    src.seek(0)
    digest = hashlib.sha256()
    size = 0
    with dest.open("xb") as out:
        while chunk := src.read(_COPY_CHUNK):
            size += len(chunk)
            if size > max_bytes:
                raise AppError(ErrorCode.FILE_TOO_LARGE,
                               f"File is too large (maximum is {max_bytes:,} bytes).",
                               details={"max_bytes": max_bytes})
            digest.update(chunk)
            out.write(chunk)
    if size == 0:
        raise AppError(ErrorCode.VALIDATION_ERROR, "The uploaded file is empty.")
    return size, digest.hexdigest()


def sweep_temp_dirs(temp_root: Path, *, max_age_seconds: float, active: Container[str],
                    now: float | None = None) -> int:
    """Remove request folders older than `max_age_seconds` that no in-flight request owns.
    The age threshold is longer than the request timeout, so folders of requests running
    in other server processes are never touched either."""
    if not temp_root.is_dir():
        return 0
    cutoff = (now or time.time()) - max_age_seconds
    removed = 0
    with os.scandir(temp_root) as entries:
        for entry in entries:
            if not (entry.is_dir(follow_symlinks=False) and HEX_ID_RE.fullmatch(entry.name)):
                continue
            if entry.name in active:
                continue
            if entry.stat(follow_symlinks=False).st_mtime >= cutoff:
                continue
            shutil.rmtree(entry.path, ignore_errors=True)
            removed += 1
    if removed:
        logger.info("temp_dirs_swept", extra={"count": removed})
    return removed
