"""
Refactored OptimizedStatusReporter - delegates to specialized helpers.

This implementation maintains the exact same output format as the original status report
while eliminating CPU spikes through performance optimizations and modular design.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from src.common.optimized_status_reporter_helpers.log_activity_formatter import (
    LogActivityFormatter,
)
from src.common.optimized_status_reporter_helpers.time_formatter import TimeFormatter
from src.common.optimized_status_reporter_mixins import (
    StatusReporterFormatterMixin,
    StatusReporterWeatherMixin,
)
from src.kalshi.api.client import KalshiClient

from .optimized_status_reporter_helpers.dependencies_factory import (
    StatusReporterDependencies,
    StatusReporterDependenciesFactory,
)
from .optimized_status_reporter_helpers.status_line import emit_status_line

logger = logging.getLogger(__name__)


class OptimizedStatusReporter(
    StatusReporterWeatherMixin,
    StatusReporterFormatterMixin,
):
    """High-performance status reporter delegating to specialized helpers."""

    def __init__(
        self,
        process_manager,
        health_checker,
        metadata_store,
        tracker_controller,
        *,
        dependencies: Optional[StatusReporterDependencies] = None,
    ):
        """Initialize reporter with all dependencies."""
        self._kalshi_client: Optional[KalshiClient] = None
        self._kalshi_client_lock = asyncio.Lock()
        self._emit_status_line = emit_status_line

        deps = dependencies or StatusReporterDependenciesFactory.create(
            process_manager,
            health_checker,
            metadata_store,
            tracker_controller,
            self._emit_status_line,
        )
        self._aggregator = deps.aggregator
        self._printer = deps.printer
        self._log_activity_formatter = LogActivityFormatter(TimeFormatter())

    async def generate_and_stream_status_report(self) -> Dict[str, Any]:
        """Generate and stream status report using optimized patterns."""

        from src.common.process_monitor import get_global_process_monitor
        from src.common.redis_protocol.connection_pool_core import get_redis_client

        try:
            redis_client = await get_redis_client()
            process_monitor = await get_global_process_monitor()
            kalshi_client = await self._get_kalshi_client()

            status_data = await self._aggregator.gather_status_data(
                redis_client, process_monitor, kalshi_client
            )
            await self._printer.print_status_report(status_data)
        except (RuntimeError, ValueError, TypeError, AttributeError, KeyError) as exc:
            logger.exception("Status report failed: %s", type(exc).__name__)
            raise RuntimeError("Status report generation failed") from exc
        else:
            return status_data

    async def _gather_status_data_optimized(self, redis_client=None) -> Dict[str, Any]:
        """
        Backward-compatible status data gathering used by monitor commands.

        When ``redis_client`` is not provided, a client is created and closed internally.
        """
        return await self.gather_status_data(redis_client=redis_client)

    async def gather_status_data(self, redis_client=None) -> Dict[str, Any]:
        """
        Preferred status data aggregation API for monitor callers.

        Creates and cleans up a Redis client when one is not provided.
        """

        from src.common.process_monitor import get_global_process_monitor
        from src.common.redis_protocol.connection_pool_core import get_redis_client as get_client

        owns_client = False
        if redis_client is None:
            redis_client = await get_client()
            owns_client = True

        try:
            process_monitor = await get_global_process_monitor()
            kalshi_client = await self._get_kalshi_client()
            return await self._aggregator.gather_status_data(
                redis_client, process_monitor, kalshi_client
            )
        finally:
            if owns_client:
                try:
                    await redis_client.aclose()
                except (
                    ConnectionError,
                    OSError,
                    RuntimeError,
                ):  # pragma: no cover - best effort cleanup
                    pass

    async def _get_kalshi_client(self) -> KalshiClient:
        """Lazily instantiate Kalshi client."""
        async with self._kalshi_client_lock:
            if self._kalshi_client is None:
                self._kalshi_client = KalshiClient()
            return self._kalshi_client
