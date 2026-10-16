"""In-process concurrency controls: admission (global and per client IP), a sliding-window
rate limiter, and backoff.

The service is stateless and keeps no job, image or user data. These counters only exist
to apply backpressure, and they are per server process. Run one uvicorn worker per
container (CPU parallelism comes from the Pillow process pool) and limits are exact per
instance.
"""

from __future__ import annotations

import contextlib
import random
import time
from collections import deque
from collections.abc import Callable, Iterator

from app.core.errors import ErrorCode, retry_after_error


def backoff_delay(attempt: int, *, base: float = 1.0, cap: float = 30.0,
                  rng: random.Random | None = None) -> float:
    """Exponential backoff with full jitter: uniform(0, min(cap, base * 2**attempt))."""
    generator = rng or random
    return generator.uniform(0, min(cap, base * (2 ** attempt)))


class SlidingWindowLimiter:
    """At most `limit` events per `window` seconds per key. Single event loop, no locks."""

    def __init__(self, limit: int, window: float = 60.0,
                 clock: Callable[[], float] = time.monotonic, max_keys: int = 100_000) -> None:
        self._limit = limit
        self._window = window
        self._clock = clock
        self._max_keys = max_keys
        self._events: dict[str, deque[float]] = {}

    def hit(self, key: str) -> float:
        """Record an event. Returns 0 if allowed, otherwise seconds until a slot frees."""
        now = self._clock()
        events = self._events.get(key)
        if events is None:
            if len(self._events) >= self._max_keys:
                self._prune(now)
            events = self._events[key] = deque()
        while events and events[0] <= now - self._window:
            events.popleft()
        if len(events) >= self._limit:
            return max(0.001, events[0] + self._window - now)
        events.append(now)
        return 0.0

    def _prune(self, now: float) -> None:
        cutoff = now - self._window
        for key in [k for k, v in self._events.items() if not v or v[-1] <= cutoff]:
            del self._events[key]


class AdmissionControl:
    """Bounds concurrent requests globally and per client. Never queues: when full, the
    caller gets an error with Retry-After immediately instead of hanging."""

    def __init__(self, *, max_total: int, max_per_client: int) -> None:
        self._max_total = max_total
        self._max_per_client = max_per_client
        self._total = 0
        self._per_client: dict[str, int] = {}

    @property
    def in_flight(self) -> int:
        return self._total

    @contextlib.contextmanager
    def admit(self, client: str) -> Iterator[None]:
        if self._per_client.get(client, 0) >= self._max_per_client:
            raise retry_after_error(
                ErrorCode.TOO_MANY_CONCURRENT_REQUESTS,
                f"You already have {self._max_per_client} images processing. "
                "Wait for one to finish.", 2)
        if self._total >= self._max_total:
            raise retry_after_error(ErrorCode.SERVER_BUSY,
                                    "The server is busy. Please retry shortly.", 5)
        self._total += 1
        self._per_client[client] = self._per_client.get(client, 0) + 1
        try:
            yield
        finally:
            self._total -= 1
            remaining = self._per_client[client] - 1
            if remaining:
                self._per_client[client] = remaining
            else:
                del self._per_client[client]
