from __future__ import annotations

import asyncio
import logging

import anyio
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import AppResources, get_resources
from app.utils.filenames import new_id

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


def _ping() -> str:
    return "pong"


@router.get("/health/live", summary="Liveness: the process is up")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health", summary="Readiness: temp storage and the processing pool")
async def ready(resources: AppResources = Depends(get_resources)) -> JSONResponse:
    checks: dict[str, str] = {}

    def temp_writable() -> None:
        probe = resources.settings.temp_dir / f".health-{new_id()}"
        try:
            probe.write_bytes(b"ok")
        finally:
            probe.unlink(missing_ok=True)

    try:
        await anyio.to_thread.run_sync(temp_writable)
        checks["temp_storage"] = "ok"
    except OSError:
        logger.warning("health_temp_storage_failed", exc_info=True)
        checks["temp_storage"] = "error"
    try:
        loop = asyncio.get_running_loop()
        await asyncio.wait_for(loop.run_in_executor(resources.executor, _ping), timeout=5)
        checks["processing_pool"] = "ok"
    except Exception:
        logger.warning("health_pool_failed", exc_info=True)
        checks["processing_pool"] = "error"

    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(status_code=200 if healthy else 503, content={
        "status": "ok" if healthy else "degraded",
        "checks": checks,
        "gemini": "configured" if resources.gemini is not None else "not_configured",
        "in_flight_requests": resources.admission.in_flight,
    })
