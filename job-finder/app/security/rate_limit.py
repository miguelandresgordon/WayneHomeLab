"""In-process login rate limiter. One worker, two users."""

from __future__ import annotations

import time
from collections import defaultdict


class LoginLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        recent = [stamp for stamp in self._hits[key] if stamp >= cutoff]
        self._hits[key] = recent
        if len(recent) >= self.max_attempts:
            return False
        self._hits[key].append(now)
        return True
