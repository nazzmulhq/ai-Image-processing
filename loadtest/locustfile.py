"""Load test: many simulated clients uploading concurrently.

    uv run locust -f loadtest/locustfile.py --host http://localhost:8000 \
        --users 30 --spawn-rate 10 --run-time 1m --headless

All simulated users share your machine's IP, so per-IP limits apply to all of them
together. 429/503 responses are the designed backpressure and are counted as successes.
To measure raw throughput, raise RATE_LIMIT_IP_PER_MINUTE and MAX_CONCURRENT_PER_IP on the
server first.
"""

from __future__ import annotations

import io
import random

from locust import HttpUser, between, task
from PIL import Image

EXPECTED = {200, 429, 503}


def make_png(width: int, height: int) -> bytes:
    color = tuple(random.randint(0, 255) for _ in range(3))
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, "PNG")
    return buffer.getvalue()


class ImageUser(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self) -> None:
        self.images = [make_png(random.randint(200, 1200), random.randint(200, 1200))
                       for _ in range(5)]

    @task(5)
    def resize_to_webp(self) -> None:
        self._process({"target_width": "256", "output_format": "WEBP", "quality": "80"})

    @task(2)
    def enhance(self) -> None:
        self._process({"enhance_image": "true"})

    @task(1)
    def capabilities(self) -> None:
        self.client.get("/api/v1/capabilities")

    def _process(self, data: dict[str, str]) -> None:
        files = {"image": ("load.png", random.choice(self.images), "image/png")}
        with self.client.post("/api/v1/images/process", files=files, data=data,
                              catch_response=True, name="/api/v1/images/process") as resp:
            if resp.status_code not in EXPECTED:
                resp.failure(f"unexpected {resp.status_code}: {resp.text[:200]}")
            else:
                resp.success()
