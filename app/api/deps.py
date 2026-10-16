"""Dependency injection. Long-lived resources are built once per process in the app lifespan
and exposed through `AppResources`; tests swap them via a resources factory."""

from __future__ import annotations

from concurrent.futures import Executor
from dataclasses import dataclass

from fastapi import Request

from app.core.concurrency import AdmissionControl, SlidingWindowLimiter
from app.core.config import Settings
from app.services.gemini_service import GeminiService
from app.services.processing_service import ImageProcessor


@dataclass
class AppResources:
    settings: Settings
    executor: Executor
    gemini: GeminiService | None
    processor: ImageProcessor
    admission: AdmissionControl
    ip_rate_limiter: SlidingWindowLimiter


def get_resources(request: Request) -> AppResources:
    return request.app.state.resources  # type: ignore[no-any-return]


def get_request_id(request: Request) -> str:
    return request.state.request_id  # type: ignore[no-any-return]


def client_ip(request: Request) -> str:
    # Behind a proxy, uvicorn's --proxy-headers/--forwarded-allow-ips sets request.client
    # from X-Forwarded-For for trusted proxies only.
    return request.client.host if request.client else "unknown"
