"""Pure-ASGI middleware (no BaseHTTPMiddleware, so streaming and contextvars behave)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id_var
from app.utils.filenames import new_id

logger = logging.getLogger("app.access")

_SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
]


def _error_body(code: str, message: str, request_id: str) -> bytes:
    return json.dumps({"success": False, "request_id": request_id,
                       "error": {"code": code, "message": message, "details": None}}).encode()


class RequestContextMiddleware:
    """Assigns a request_id, adds it (and security headers) to every response, writes a
    structured access log without query strings, and turns unhandled exceptions into a
    generic 500 response that leaks no internals."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = new_id()
        scope.setdefault("state", {})["request_id"] = request_id
        request_id_var.set(request_id)
        started = time.perf_counter()
        status_holder: dict[str, Any] = {"status": 500, "started": False}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                status_holder["started"] = True
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                headers.extend(_SECURITY_HEADERS)
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception("unhandled_exception")
            if not status_holder["started"]:
                body = _error_body("INTERNAL_ERROR", "An unexpected error occurred.", request_id)
                await send_wrapper({"type": "http.response.start", "status": 500, "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode())]})
                await send({"type": "http.response.body", "body": body})
        finally:
            logger.info("request", extra={
                "method": scope.get("method"),
                "path": scope.get("path"),  # never the query string
                "status": status_holder["status"],
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            })


class BodySizeLimitMiddleware:
    """Rejects request bodies larger than `max_body_bytes` with 413, both from the
    Content-Length header and while streaming (chunked uploads)."""

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in ("POST", "PUT", "PATCH"):
            await self.app(scope, receive, send)
            return
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    declared = 0
                if declared > self.max_body_bytes:
                    await self._reject(scope, send)
                    return
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    # FastAPI re-raises HTTPException from body parsing; our handler maps 413.
                    raise HTTPException(status_code=413)
            return message

        await self.app(scope, limited_receive, send)

    async def _reject(self, scope: Scope, send: Send) -> None:
        request_id = scope.get("state", {}).get("request_id", "")
        body = _error_body("FILE_TOO_LARGE", "Request body is too large.", request_id)
        await send({"type": "http.response.start", "status": 413, "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            (b"connection", b"close")]})
        await send({"type": "http.response.body", "body": body})
