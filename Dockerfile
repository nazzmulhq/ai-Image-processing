# syntax=docker/dockerfile:1.7

FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY app ./app
COPY scripts ./scripts

FROM python:3.13-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/app/.venv/bin:$PATH"
RUN groupadd --system app && useradd --system --gid app --home-dir /app app \
    && mkdir -p /tmp/imgproc && chown app:app /tmp/imgproc && chmod 700 /tmp/imgproc
WORKDIR /app
COPY --from=builder --chown=app:app /app /app
USER app
ENV TEMP_DIR=/tmp/imgproc
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3).status == 200 else 1)"
# One uvicorn worker: CPU parallelism comes from the Pillow process pool (CPU_WORKERS), and
# per-IP limits stay exact. Scale out with more containers behind a load balancer.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-access-log"]
