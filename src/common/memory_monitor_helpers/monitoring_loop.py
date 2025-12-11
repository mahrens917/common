"""Monitoring loop for memory monitoring."""

import asyncio
import logging
from typing import Optional

import psutil

from .alert_logger import AlertLogger
from .snapshot_collector import SnapshotCollector
from .trend_analyzer import TrendAnalyzer

logger = logging.getLogger(__name__)

PSUTIL_ERRORS = (psutil.Error, OSError)
TASK_QUERY_ERRORS = (RuntimeError, ValueError)
COLLECTION_ERRORS = (RuntimeError, ValueError, KeyError, AttributeError, TypeError)
MONITOR_LOOP_ERRORS = PSUTIL_ERRORS + TASK_QUERY_ERRORS + COLLECTION_ERRORS + (asyncio.TimeoutError,)


class MonitoringLoop:
    """Manages the background monitoring loop."""

    def __init__(
        self,
        snapshot_collector: SnapshotCollector,
        trend_analyzer: TrendAnalyzer,
        alert_logger: AlertLogger,
        check_interval_seconds: int,
    ):
        """
        Initialize monitoring loop.

        Args:
            snapshot_collector: Collector for memory snapshots
            trend_analyzer: Analyzer for trend detection
            alert_logger: Logger for alerts
            check_interval_seconds: Time between checks
        """
        self.snapshot_collector = snapshot_collector
        self.trend_analyzer = trend_analyzer
        self.alert_logger = alert_logger
        self.check_interval_seconds = check_interval_seconds
        self.monitoring_task: Optional[asyncio.Task] = None
        self.shutdown_requested = False

    async def start_monitoring(self) -> None:
        """Start background memory monitoring."""
        if self.monitoring_task is not None:
            logger.warning("Memory monitoring already started")
            return

        logger.info(f"Starting memory monitoring (interval: {self.check_interval_seconds}s)")
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self) -> None:
        """Stop background memory monitoring."""
        if self.monitoring_task is None:
            return

        logger.info("Stopping memory monitoring")
        self.shutdown_requested = True

        if not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                logger.debug("Memory monitoring task cancelled during shutdown")

        self.monitoring_task = None

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        logger.info("Memory monitoring loop started")

        while not self.shutdown_requested:
            try:
                # Take snapshot
                snapshot = self.snapshot_collector.take_snapshot()

                # Analyze trends
                snapshots = self.snapshot_collector.get_snapshots()
                analysis = self.trend_analyzer.analyze_memory_trends(snapshots)

                # Log alerts
                self.alert_logger.log_alerts(analysis)

                # Log periodic status
                logger.debug(
                    f"Memory status: {snapshot.process_memory_mb:.1f}MB process, "
                    f"{snapshot.system_memory_percent:.1f}% system, "
                    f"{snapshot.task_count} tasks, "
                    f"collections: {snapshot.collection_sizes}"
                )

                # Wait for next check
                await asyncio.sleep(self.check_interval_seconds)

            except asyncio.CancelledError:
                logger.info("Memory monitoring loop cancelled")
                break
            except MONITOR_LOOP_ERRORS:
                # Error in monitoring - continue with next iteration
                await asyncio.sleep(self.check_interval_seconds)

        logger.info("Memory monitoring loop ended")

    def is_monitoring_active(self) -> bool:
        """Check if monitoring is currently active."""
        return self.monitoring_task is not None and not self.monitoring_task.done()
