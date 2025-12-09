"""
Reactive Rate Limiter - Simple 429-based rate limiting for Kalshi API

Provides reactive rate limiting that responds to actual 429 responses from the API
rather than trying to predict rate limits with complex token bucket algorithms.
"""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


# Constants
_CONST_3 = 3


class ReactiveRateLimiter:
    """Simple reactive rate limiter that responds to 429 responses with exponential backoff."""

    def __init__(self, base_delay: float = 1.0, error_analyzer=None):
        self.backoff_until = 0.0
        self.consecutive_429s = 0
        self.base_delay = base_delay
        self.error_analyzer = error_analyzer
        logger.info("[ReactiveRateLimiter] Initialized with base_delay=%ss", base_delay)

    async def is_in_backoff(self) -> bool:
        return time.time() < self.backoff_until

    async def wait_if_needed(self) -> None:
        current_time = time.time()
        if current_time < self.backoff_until:
            wait_time = self.backoff_until - current_time
            logger.info("[ReactiveRateLimiter] Rate limited - waiting %.2fs", wait_time)
            await asyncio.sleep(wait_time)

    def handle_429_response(self) -> float:
        self.consecutive_429s += 1
        delay = self.base_delay * (2 ** min(self.consecutive_429s - 1, 5))
        self.backoff_until = time.time() + delay
        logger.warning(
            "[ReactiveRateLimiter] 429 detected - backing off for %ss (attempt #%s)",
            delay,
            self.consecutive_429s,
        )
        return delay

    async def reset_backoff(self) -> None:
        had_failures = self.consecutive_429s > 0
        if had_failures:
            logger.info(
                "[ReactiveRateLimiter] Request successful - resetting backoff (was at %s consecutive 429s)",
                self.consecutive_429s,
            )
            if self.error_analyzer and self.consecutive_429s >= _CONST_3:
                await self.error_analyzer.report_recovery(
                    "Rate limit recovery", {"previous_failures": self.consecutive_429s}
                )
        self.consecutive_429s = 0

    def get_metrics(self) -> dict:
        current_time = time.time()
        return {
            "consecutive_429s": self.consecutive_429s,
            "backoff_until": self.backoff_until,
            "is_in_backoff": current_time < self.backoff_until,
            "time_until_backoff_expires": max(0, self.backoff_until - current_time),
            "base_delay": self.base_delay,
            "timestamp": current_time,
        }
