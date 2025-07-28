"""Rate limiter using token bucket algorithm."""

import threading
import time


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, requests_per_minute: int):
        self.rate = requests_per_minute / 60.0  # Convert to per second
        self.capacity = requests_per_minute
        self.tokens = float(requests_per_minute)
        self.last_update = time.time()
        self._lock = threading.RLock()

    def _update_tokens(self) -> None:
        """Update available tokens based on time passed."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

    def check(self) -> bool:
        """Check if request can be made without consuming token."""
        with self._lock:
            self._update_tokens()
            return self.tokens >= 1.0

    def consume(self) -> bool:
        """Try to consume a token. Returns True if successful."""
        with self._lock:
            self._update_tokens()
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False

    def get_wait_time(self) -> float:
        """Get seconds to wait until next token is available."""
        with self._lock:
            self._update_tokens()
            if self.tokens >= 1.0:
                return 0.0

            tokens_needed = 1.0 - self.tokens
            wait_time = tokens_needed / self.rate
            return wait_time

    def get_remaining(self) -> int:
        """Get number of remaining requests."""
        with self._lock:
            self._update_tokens()
            return int(self.tokens)

    def get_reset_time(self) -> float:
        """Get Unix timestamp when rate limit resets to full capacity."""
        with self._lock:
            self._update_tokens()
            if self.tokens >= self.capacity:
                return time.time()

            tokens_needed = self.capacity - self.tokens
            seconds_until_full = tokens_needed / self.rate
            return time.time() + seconds_until_full
