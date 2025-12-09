"""Shared health check types and helpers."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, NamedTuple


class HealthCheckResult(NamedTuple):
    """Standard result for health checks."""

    healthy: bool
    details: dict[str, Any] | None = None
    error: str | None = None


class BaseHealthMonitor(ABC):
    """Abstract base for protocol-specific health monitors."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.last_success_time = 0.0
        self.consecutive_failures = 0
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    @abstractmethod
    async def check_health(self) -> HealthCheckResult:
        """Perform a health check and return a standardized result."""

    def record_success(self, *, timestamp: float | None = None) -> None:
        """Update counters after a successful check."""
        loop = asyncio.get_running_loop()
        self.last_success_time = timestamp if timestamp is not None else loop.time()
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        """Update counters after a failed check."""
        self.consecutive_failures += 1

    def reset_counters(self) -> None:
        """Reset tracked counters."""
        self.consecutive_failures = 0
        self.last_success_time = 0.0

    def increment_failures(self) -> None:
        """Alias for incrementing failure count."""
        self.record_failure()

    def reset_failures(self) -> None:
        """Alias for resetting failure state."""
        self.reset_counters()

    def should_raise_error(self, threshold: int) -> bool:
        """Determine if failure count meets threshold for escalation."""
        return self.consecutive_failures >= threshold
