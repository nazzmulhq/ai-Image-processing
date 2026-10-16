"""Structured JSON logging with the request id carried in a contextvar.

Never pass image bytes or API keys to a logger; only identifiers, sizes and timings.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

_STANDARD_ATTRS = frozenset(vars(logging.makeLogRecord({})).keys()) | {"message", "asctime"}
_SAFE_TYPES = (str, int, float, bool, type(None))


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None) or request_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        for key, value in record.__dict__.items():
            if key in _STANDARD_ATTRS or key in payload or key.startswith("_"):
                continue
            # Only simple values: never serialise arbitrary objects (could be bytes/secrets).
            if isinstance(value, _SAFE_TYPES):
                payload[key] = value
            elif isinstance(value, (list, tuple)) and all(
                isinstance(v, _SAFE_TYPES) for v in value
            ):
                payload[key] = list(value)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    # Our own access log omits query strings (media signatures); silence uvicorn's.
    logging.getLogger("uvicorn.access").disabled = True
    for noisy in ("httpx", "httpcore", "google_genai", "urllib3", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
