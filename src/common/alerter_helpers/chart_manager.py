"""Chart management helper for Alerter."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, Optional, Protocol, Tuple

from ..chart_generator import ChartGenerator

logger = logging.getLogger(__name__)


class PnlReporterProtocol(Protocol):
    """Protocol for PnlReporter from monitor package."""

    async def initialize(self) -> None: ...

    async def build_full_report(self, target_date: Optional[date] = None) -> Tuple[str, Dict[str, Any]]: ...


class OptimizedHistoryMetricsRecorderProtocol(Protocol):
    """Protocol for OptimizedHistoryMetricsRecorder from monitor package."""

    ...


class ChartManager:
    """Manages chart generation dependencies and initialization."""

    def __init__(self, telegram_enabled: bool):
        """Initialize chart manager."""
        self.telegram_enabled = telegram_enabled
        self.chart_generator: Optional[ChartGenerator] = None
        self.history_metrics_recorder: Optional[OptimizedHistoryMetricsRecorderProtocol] = None
        self.pnl_reporter: Optional[PnlReporterProtocol] = None

    def set_metrics_recorder(self, recorder: OptimizedHistoryMetricsRecorderProtocol) -> None:
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

    async def ensure_pnl_reporter(self) -> PnlReporterProtocol:
        """Ensure PnL reporter is initialized."""
        reporter = self.pnl_reporter
        if reporter is None:
            try:
                import importlib

                pnl_module = importlib.import_module("src.monitor.pnl_reporter")
                pnl_cls = getattr(pnl_module, "PnlReporter")
                reporter = pnl_cls()
                self.pnl_reporter = reporter
            except (ImportError, AttributeError) as exc:
                raise ImportError("monitor package must be installed to use PnlReporter") from exc
        await reporter.initialize()
        return reporter
