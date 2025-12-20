"""Chart management helper for Alerter."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from ..chart_generator import ChartGenerator
from ..pnl_reporter import PnlReporter

if TYPE_CHECKING:
    from src.monitor.optimized_history_metrics_recorder import OptimizedHistoryMetricsRecorder

logger = logging.getLogger(__name__)


class ChartManager:
    """Manages chart generation dependencies and initialization."""

    def __init__(self, telegram_enabled: bool):
        """Initialize chart manager."""
        self.telegram_enabled = telegram_enabled
        self.chart_generator: Optional[ChartGenerator] = None
        self.history_metrics_recorder: Optional[OptimizedHistoryMetricsRecorder] = None
        self.pnl_reporter: Optional[PnlReporter] = None

    def set_metrics_recorder(self, recorder: OptimizedHistoryMetricsRecorder) -> None:
        """Set metrics recorder instance."""
        self.history_metrics_recorder = recorder

    def ensure_chart_dependencies_initialized(self) -> None:
        """Lazily initialize chart dependencies."""
        if not self.telegram_enabled or self.chart_generator:
            return
        try:
            self.chart_generator = ChartGenerator()
            logger.debug("Chart generator initialized")
        except (OSError, RuntimeError, ImportError):
            logger.exception("Failed to initialize chart generator")
            raise

    async def ensure_pnl_reporter(self) -> PnlReporter:
        """Ensure PnL reporter is initialized."""
        if self.pnl_reporter is None:
            self.pnl_reporter = PnlReporter()
        await self.pnl_reporter.initialize()
        return self.pnl_reporter
