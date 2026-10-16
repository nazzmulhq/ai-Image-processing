"""Consistent error responses: {success: false, request_id, error: {code, message, details}}.
Never includes stack traces, file paths, upstream payloads or secrets."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError, ErrorCode
from app.schemas.errors import ErrorBody, ErrorResponse

_HTTP_CODES: dict[int, tuple[ErrorCode, str]] = {
    400: (ErrorCode.BAD_REQUEST, "The request could not be parsed."),
    404: (ErrorCode.NOT_FOUND, "Resource not found."),
    405: (ErrorCode.METHOD_NOT_ALLOWED, "Method not allowed."),
    413: (ErrorCode.FILE_TOO_LARGE, "Request body is too large."),
}


def error_response(*, status_code: int, code: str, message: str, request_id: str | None,
                   details: Any = None, headers: dict[str, str] | None = None) -> JSONResponse:
    body = ErrorResponse(request_id=request_id,
                         error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"),
                        headers=headers)


def validation_details(errors: Sequence[Any]) -> list[dict[str, Any]]:
    """Field errors without echoing the submitted input back."""
    details = []
    for err in errors:
        loc = [str(part) for part in err.get("loc", ()) if part not in ("body",)]
        details.append({"field": ".".join(loc) or None, "message": err.get("msg", "invalid"),
                        "type": err.get("type")})
    return details


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return error_response(status_code=exc.status_code, code=exc.code, message=exc.message,
                              request_id=_request_id(request), details=exc.details,
                              headers=exc.headers or None)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(status_code=422, code=ErrorCode.VALIDATION_ERROR,
                              message="Request validation failed.",
                              request_id=_request_id(request),
                              details=validation_details(exc.errors()))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, message = _HTTP_CODES.get(exc.status_code,
                                        (ErrorCode.BAD_REQUEST, "The request failed."))
        if exc.status_code >= 500:
            code, message = ErrorCode.INTERNAL_ERROR, "An unexpected error occurred."
        return error_response(status_code=exc.status_code, code=code, message=message,
                              request_id=_request_id(request),
                              headers=getattr(exc, "headers", None))
