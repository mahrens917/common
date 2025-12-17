"""Rate limiter for API request throttling.

Aggressive backoff-only strategy: runs at full speed until rate limited,
then backs off exponentially. A single success clears backoff completely.

Used by: peak, kalshi, and other trading system repositories.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, Optional

# Rate limiter configuration constants
INITIAL_BACKOFF_MS = 1000.0
MAX_BACKOFF_MS = 30000.0
BACKOFF_MULTIPLIER = 2.0


@dataclass
class RateLimiterConfig:
    """Configuration for rate limiter."""

    initial_backoff_ms: float = field(default_factory=lambda: INITIAL_BACKOFF_MS)
    max_backoff_ms: float = field(default_factory=lambda: MAX_BACKOFF_MS)
    backoff_multiplier: float = field(default_factory=lambda: BACKOFF_MULTIPLIER)


class RateLimiter:
    """Aggressive rate limiter with full-speed operation until rate limited.

    Strategy:
    - Runs at full speed (0 delay) until rate limited
    - On rate limit: starts exponential backoff
    - On success: immediately clears backoff (back to full speed)
    - Non-rate-limit errors don't affect backoff
    """

    def __init__(self, config: Optional[RateLimiterConfig] = None) -> None:
        self._config = config if config is not None else RateLimiterConfig()
        self._current_delay_ms: float = 0.0
        self._total_requests = 0
        self._total_rate_limits = 0
        self._total_errors = 0
        self._is_backing_off = False

    @property
    def current_delay_ms(self) -> float:
        """Return current delay in milliseconds."""
        return self._current_delay_ms

    @property
    def stats(self) -> Dict[str, int | float | bool]:
        """Return rate limiter statistics."""
        return {
            "total_requests": self._total_requests,
            "total_rate_limits": self._total_rate_limits,
            "total_errors": self._total_errors,
            "current_delay_ms": self._current_delay_ms,
            "is_backing_off": self._is_backing_off,
        }

    async def wait(self) -> None:
        """Wait for the current delay before making a request."""
        self._total_requests += 1
        if self._current_delay_ms > 0:
            await asyncio.sleep(self._current_delay_ms / 1000.0)

    def record_success(self) -> None:
        """Record a successful request, clearing any backoff."""
        self._current_delay_ms = 0.0
        self._is_backing_off = False

    def record_rate_limit(self, retry_after_seconds: Optional[float] = None) -> float:
        """Record a rate limit response, triggering or increasing backoff.

        Args:
            retry_after_seconds: Optional Retry-After header value in seconds

        Returns:
            The new delay in milliseconds
        """
        self._total_rate_limits += 1

        if retry_after_seconds is not None:
            # Use server-provided retry delay
            self._current_delay_ms = retry_after_seconds * 1000.0
        elif not self._is_backing_off:
            # First rate limit: start backoff
            self._current_delay_ms = self._config.initial_backoff_ms
        else:
            # Consecutive rate limit: increase backoff
            self._current_delay_ms = min(
                self._config.max_backoff_ms,
                self._current_delay_ms * self._config.backoff_multiplier,
            )

        self._is_backing_off = True
        return self._current_delay_ms

    def handle_429_response(self, retry_after_seconds: Optional[float] = None) -> float:
        """Compatibility alias for record_rate_limit."""
        return self.record_rate_limit(retry_after_seconds)

    def record_error(self) -> None:
        """Record a non-rate-limit error (no effect on backoff)."""
        self._total_errors += 1
        # Non-rate-limit errors don't affect backoff state

    def get_metrics(self) -> Dict[str, int | float | bool]:
        """Compatibility alias for stats property."""
        return self.stats

    def reset(self) -> None:
        """Reset rate limiter state to initial values."""
        self._current_delay_ms = 0.0
        self._is_backing_off = False
        self._total_requests = 0
        self._total_rate_limits = 0
        self._total_errors = 0


__all__ = ["RateLimiter", "RateLimiterConfig"]
