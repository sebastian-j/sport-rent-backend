import math
import time
from collections import deque
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after: int | None = None


class SlidingWindowRateLimiter:
    def __init__(self, window_seconds: int) -> None:
        self._window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = {}
        self._lock = Lock()
        self._last_cleanup = time.monotonic()

    def check(self, limits: dict[str, int]) -> RateLimitDecision:
        now = time.monotonic()
        window_start = now - self._window_seconds

        with self._lock:
            if now - self._last_cleanup >= min(60, self._window_seconds):
                self._remove_expired_entries(window_start)
                self._last_cleanup = now

            retry_after = 0

            for key, limit in limits.items():
                attempts = self._attempts.setdefault(key, deque())
                self._discard_expired(attempts, window_start)

                if len(attempts) >= limit:
                    retry_after = max(
                        retry_after,
                        math.ceil(attempts[0] + self._window_seconds - now),
                    )

            if retry_after:
                return RateLimitDecision(
                    allowed=False,
                    retry_after=max(1, retry_after),
                )

            for key in limits:
                self._attempts[key].append(now)

        return RateLimitDecision(allowed=True)

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()
            self._last_cleanup = time.monotonic()

    @staticmethod
    def _discard_expired(attempts: deque[float], window_start: float) -> None:
        while attempts and attempts[0] <= window_start:
            attempts.popleft()

    def _remove_expired_entries(self, window_start: float) -> None:
        for attempts in self._attempts.values():
            self._discard_expired(attempts, window_start)

        empty_keys = [key for key, attempts in self._attempts.items() if not attempts]
        for key in empty_keys:
            del self._attempts[key]
