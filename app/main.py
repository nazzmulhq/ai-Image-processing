"""FastAPI application factory.

Run locally:  uv run uvicorn app.main:app --reload
Production:   uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
              (one uvicorn worker per container: CPU parallelism comes from the Pillow
              process pool, and per-IP limits stay exact)
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import anyio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from starlette.responses import Response

from app.api.deps import AppResources
from app.api.errors import register_exception_handlers
from app.api.middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from app.api.routes import health, images
from app.core.concurrency import AdmissionControl, SlidingWindowLimiter
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.services.gemini_service import GeminiService, GoogleGeminiService
from app.services.pipeline_stages import init_worker
from app.services.processing_service import ImageProcessor
from app.services.workspace import ensure_temp_root, sweep_temp_dirs

logger = logging.getLogger(__name__)

ResourcesFactory = Callable[[Settings], Awaitable[AppResources]]

STATIC_DIR = Path(__file__).parent / "static"
# Multipart framing + form fields on top of the image itself.
_MULTIPART_OVERHEAD = 1024 * 1024


def _warm() -> None:
    return None


class RevalidatingStaticFiles(StaticFiles):
    """The page's script and styles. `no-cache` makes the browser re-check them on every load
    (an unchanged file is a cheap 304), so an update is never hidden behind a stale copy."""

    def file_response(self, *args: Any, **kwargs: Any) -> Response:
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


def _index_html() -> str:
    """The page, with its script and stylesheet links versioned by file modification time
    (`/static/app.js?v=...`). Any change gives a new URL, so even a browser holding an old
    cached copy loads the current file."""
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    for name in ("app.js", "styles.css"):
        version = (STATIC_DIR / name).stat().st_mtime_ns
        html = html.replace(f'"/static/{name}"', f'"/static/{name}?v={version}"')
    return html


async def build_resources(settings: Settings) -> AppResources:
    Image.MAX_IMAGE_PIXELS = settings.max_image_pixels
    ensure_temp_root(settings.temp_dir)
    executor = ProcessPoolExecutor(max_workers=settings.cpu_workers, initializer=init_worker,
                                   initargs=(settings.max_image_pixels,),
                                   max_tasks_per_child=200)
    loop = asyncio.get_running_loop()
    # Start the pool processes now so the first requests don't pay the spawn cost.
    await asyncio.gather(*(loop.run_in_executor(executor, _warm)
                           for _ in range(settings.cpu_workers)))
    gemini: GeminiService | None = (GoogleGeminiService.from_settings(settings)
                                    if settings.gemini_configured else None)
    return assemble_resources(settings, executor, gemini)


def assemble_resources(settings: Settings, executor: ProcessPoolExecutor | object,
                       gemini: GeminiService | None) -> AppResources:
    return AppResources(
        settings=settings, executor=executor, gemini=gemini,  # type: ignore[arg-type]
        processor=ImageProcessor(settings=settings, executor=executor,  # type: ignore[arg-type]
                                 gemini=gemini),
        admission=AdmissionControl(max_total=settings.max_concurrent_requests,
                                   max_per_client=settings.max_concurrent_per_ip),
        ip_rate_limiter=SlidingWindowLimiter(settings.rate_limit_ip_per_minute, 60.0),
    )


async def close_resources(resources: AppResources) -> None:
    if resources.gemini is not None:
        with contextlib.suppress(Exception):
            await resources.gemini.aclose()
    await anyio.to_thread.run_sync(lambda: resources.executor.shutdown(wait=True,
                                                                       cancel_futures=True))


async def _sweep_forever(resources: AppResources) -> None:
    settings = resources.settings
    while True:
        try:
            await anyio.to_thread.run_sync(lambda: sweep_temp_dirs(
                settings.temp_dir, max_age_seconds=settings.temp_max_age_seconds,
                active=set(resources.processor.active_requests)))
        except Exception:
            logger.warning("temp_sweep_failed", exc_info=True)
        await asyncio.sleep(settings.temp_sweep_interval_seconds)


def create_app(settings: Settings | None = None,
               resources_factory: ResourcesFactory = build_resources) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resources = await resources_factory(settings)
        app.state.resources = resources
        sweeper = asyncio.create_task(_sweep_forever(resources))
        try:
            yield
        finally:
            sweeper.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await sweeper
            await close_resources(resources)

    app = FastAPI(
        title=settings.app_name,
        version="2.0.0",
        description=(
            "Stateless image processing: upload an image, optionally detect objects with "
            "Google Gemini, and resize/convert/compress it with Pillow. The processed image "
            "is returned inline; nothing is stored. No login required."
        ),
        lifespan=lifespan,
    )
    register_exception_handlers(app)

    # Starlette runs the last-added middleware first: RequestContext is outermost.
    app.add_middleware(BodySizeLimitMiddleware,
                       max_body_bytes=settings.max_upload_bytes + _MULTIPART_OVERHEAD)
    if settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type"],
            expose_headers=["Retry-After", "X-Request-ID"],
            max_age=600,
        )
    app.add_middleware(RequestContextMiddleware)

    app.include_router(images.router)
    app.include_router(health.router)

    if settings.serve_frontend:
        app.mount("/static", RevalidatingStaticFiles(directory=STATIC_DIR), name="static")

        @app.get("/", include_in_schema=False)
        async def index() -> HTMLResponse:
            html = await anyio.to_thread.run_sync(_index_html)
            return HTMLResponse(html, headers={"Cache-Control": "no-cache"})

    return app


def __getattr__(name: str) -> FastAPI:
    # `uvicorn app.main:app` builds the app lazily so importing this module (e.g. in tests or
    # in process-pool children) has no side effects.
    if name == "app":
        application = create_app()
        globals()["app"] = application
        return application
    raise AttributeError(name)


def __dir__() -> list[str]:
    # `dir(module)` doesn't probe `__getattr__`, so tools that discover an ASGI app by
    # enumerating module attributes (e.g. `fastapi dev`, which checks `"app" in dir(mod)`)
    # need "app" listed here even though it's only built on first access.
    return [*globals(), "app"]
