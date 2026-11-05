"""In-memory limit on failed logins. Per process, which is correct with one Modal container."""
import math
import threading
import time
from typing import Callable, Dict, Tuple


class LoginThrottle:
    """Blocks a key once it has too many failures within one time window."""

    def __init__(
        self,
        max_failures: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._max_failures = max_failures
        self._window_seconds = window_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._failures: Dict[str, Tuple[int, float]] = {}  # key -> (count, window start)

    def retry_after(self, key: str) -> int:
        """Seconds until this key may try again; 0 if it is not blocked."""
        with self._lock:
            count, started = self._failures.get(key, (0, 0.0))
            remaining = started + self._window_seconds - self._clock()
            if count < self._max_failures or remaining <= 0:
                return 0
            return math.ceil(remaining)

    def record_failure(self, key: str) -> None:
        now = self._clock()
        with self._lock:
            self._forget_expired(now)
            count, started = self._failures.get(key, (0, now))
            self._failures[key] = (count + 1, started)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()

    def tracked_keys(self) -> int:
        with self._lock:
            return len(self._failures)

    def _forget_expired(self, now: float) -> None:
        expired = [key for key, (_, started) in self._failures.items() if started + self._window_seconds <= now]
        for key in expired:
            del self._failures[key]
