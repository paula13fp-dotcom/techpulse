"""Token bucket rate limiter for polite scraping."""
import time
import threading


class RateLimiter:
    def __init__(self, calls_per_second: float = 0.5):
        self._min_interval = 1.0 / calls_per_second
        self._last_call = 0.0
        self._lock = threading.Lock()

    def wait(self):
        with self._lock:
            elapsed = time.monotonic() - self._last_call
            wait_time = self._min_interval - elapsed
            if wait_time > 0:
                time.sleep(wait_time)
            self._last_call = time.monotonic()
