"""Reconnection logic with backoff."""

import asyncio
import logging
import random

_SECURE_RANDOM = random.SystemRandom()


class ReconnectionHandler:
    """Handles reconnection with exponential backoff."""

    def __init__(
        self,
        service_name: str,
        initial_delay: float,
        max_delay: float,
        backoff_multiplier: float,
        max_failures: int,
        metrics_tracker,
    ):
        self.service_name = service_name
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.max_failures = max_failures
        self.metrics_tracker = metrics_tracker
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    def calculate_backoff_delay(self) -> float:
        """Calculate exponential backoff delay."""
        metrics = self.metrics_tracker.get_metrics()
        if metrics.consecutive_failures == 0:
            return 0.0

        delay = self.initial_delay * (self.backoff_multiplier ** (metrics.consecutive_failures - 1))
        delay = min(delay, self.max_delay)

        jitter = delay * 0.2 * (_SECURE_RANDOM.random() - 0.5)
        delay += jitter

        self.metrics_tracker.set_backoff_delay(delay)
        return delay

    def should_retry(self) -> bool:
        """Check if should attempt reconnection."""
        metrics = self.metrics_tracker.get_metrics()
        return metrics.consecutive_failures < self.max_failures

    async def apply_backoff(self) -> bool:
        """Apply backoff delay if needed."""
        metrics = self.metrics_tracker.get_metrics()
        if metrics.consecutive_failures > 0:
            backoff_delay = self.calculate_backoff_delay()
            self.logger.info(f"Waiting {backoff_delay:.1f}s before reconnection attempt " f"(failure #{metrics.consecutive_failures})")
            await asyncio.sleep(backoff_delay)
            return True
        return False

    async def reconnect(self):
        """
        Main reconnection method - default stub implementation.
        """
        return None
