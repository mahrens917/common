"""Shared initializer for PnL calculator helpers."""

from ..redis_protocol.trade_store import TradeStore
from .report_generator import ReportGenerator


class BaseReportOperations:
    """Provides shared wiring for trade store/report generator pairs."""

    def __init__(self, trade_store: TradeStore, report_generator: ReportGenerator, logger):
        self.trade_store = trade_store
        self.report_generator = report_generator
        self.logger = logger


__all__ = ["BaseReportOperations"]
