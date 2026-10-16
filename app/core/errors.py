"""Application error type and the catalogue of stable error codes returned to clients."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    # Request / input
    BAD_REQUEST = "BAD_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    OUTPUT_TOO_LARGE = "OUTPUT_TOO_LARGE"
    CORRUPTED_IMAGE = "CORRUPTED_IMAGE"
    ANIMATED_IMAGE_UNSUPPORTED = "ANIMATED_IMAGE_UNSUPPORTED"
    FEATURE_NOT_CONFIGURED = "FEATURE_NOT_CONFIGURED"

    # Limits / capacity
    RATE_LIMITED = "RATE_LIMITED"
    TOO_MANY_CONCURRENT_REQUESTS = "TOO_MANY_CONCURRENT_REQUESTS"
    SERVER_BUSY = "SERVER_BUSY"

    # Gemini
    GEMINI_RATE_LIMITED = "GEMINI_RATE_LIMITED"
    GEMINI_SAFETY_BLOCKED = "GEMINI_SAFETY_BLOCKED"
    GEMINI_INVALID_RESPONSE = "GEMINI_INVALID_RESPONSE"
    GEMINI_REQUEST_REJECTED = "GEMINI_REQUEST_REJECTED"
    GEMINI_UNAVAILABLE = "GEMINI_UNAVAILABLE"
    GEMINI_TIMEOUT = "GEMINI_TIMEOUT"
    GEMINI_CONFIGURATION_ERROR = "GEMINI_CONFIGURATION_ERROR"

    # Processing
    PROCESSING_FAILED = "PROCESSING_FAILED"
    PROCESSING_TIMEOUT = "PROCESSING_TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


HTTP_STATUS_FOR_CODE: dict[ErrorCode, int] = {
    ErrorCode.BAD_REQUEST: 400,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.METHOD_NOT_ALLOWED: 405,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.UNSUPPORTED_FILE_TYPE: 415,
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.IMAGE_TOO_LARGE: 413,
    ErrorCode.OUTPUT_TOO_LARGE: 422,
    ErrorCode.CORRUPTED_IMAGE: 422,
    ErrorCode.ANIMATED_IMAGE_UNSUPPORTED: 422,
    ErrorCode.FEATURE_NOT_CONFIGURED: 422,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.TOO_MANY_CONCURRENT_REQUESTS: 429,
    ErrorCode.SERVER_BUSY: 503,
    ErrorCode.GEMINI_RATE_LIMITED: 503,
    ErrorCode.GEMINI_SAFETY_BLOCKED: 422,
    ErrorCode.GEMINI_INVALID_RESPONSE: 502,
    ErrorCode.GEMINI_REQUEST_REJECTED: 502,
    ErrorCode.GEMINI_UNAVAILABLE: 502,
    ErrorCode.GEMINI_TIMEOUT: 504,
    ErrorCode.GEMINI_CONFIGURATION_ERROR: 503,
    ErrorCode.PROCESSING_FAILED: 500,
    ErrorCode.PROCESSING_TIMEOUT: 504,
    ErrorCode.INTERNAL_ERROR: 500,
}


class AppError(Exception):
    """An expected failure with a stable code and a client-safe message.

    The message is shown to API clients, so it must never contain secrets, file system
    paths, stack traces or raw upstream responses. AppError is picklable so it can cross
    the process-pool boundary unchanged.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        status_code: int | None = None,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code or HTTP_STATUS_FOR_CODE.get(code, 400)
        self.details = details
        self.headers = headers or {}

    def __reduce__(self) -> tuple[Any, ...]:
        return (_rebuild_app_error,
                (str(self.code), self.message, self.status_code, self.details, self.headers))

    def __repr__(self) -> str:
        return f"AppError(code={self.code!s}, status={self.status_code}, message={self.message!r})"


def _rebuild_app_error(code: str, message: str, status_code: int, details: Any,
                       headers: dict[str, str]) -> AppError:
    return AppError(ErrorCode(code), message, status_code=status_code, details=details,
                    headers=headers)


def retry_after_error(code: ErrorCode, message: str, retry_after: float) -> AppError:
    seconds = max(1, int(retry_after + 0.999))
    return AppError(code, message, headers={"Retry-After": str(seconds)},
                    details={"retry_after_seconds": seconds})
