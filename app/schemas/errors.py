from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    success: Literal[False] = False
    request_id: str | None = None
    error: ErrorBody
