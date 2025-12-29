"""
Human-readable status reporting for trading operations.
Provides clean, concise status updates without verbose logging prefixes.
"""

import logging
from typing import Optional

from .status_reporter_helpers import (
    MessageFormatter,
    OpportunityReporter,
    OutputWriter,
    SummaryBuilder,
    TimeFormatter,
    TradeReporter,
)

logger = logging.getLogger(__name__)


class _MarketStatusHelper:
    def __init__(self, writer_write):
        self._write = writer_write

    def tracking_started(self) -> None:
        self._write(MessageFormatter.tracking_started())

    def markets_closed(self) -> None:
        self._write(MessageFormatter.markets_closed())

    def markets_open(self) -> None:
        self._write(MessageFormatter.markets_open())

    def scanning_markets(self, market_count: int) -> None:
        self._write(MessageFormatter.scanning_markets(market_count))

    def opportunities_summary(self, opportunities_found: int, trades_executed: int, markets_closed: int = 0) -> None:
        message = SummaryBuilder.build_opportunities_summary(opportunities_found, trades_executed, markets_closed)
        self._write(message)

    def checking_market_hours(self) -> None:
        self._write(MessageFormatter.checking_market_hours())


class _TradeStatusHelper:
    def __init__(self, writer_write):
        self._write = writer_write

    def trade_opportunity_found(
        self,
        ticker: str,
        action: str,
        side: str,
        price_cents: int,
        reason: str,
        weather_context: Optional[str] = None,
    ) -> None:
        message = OpportunityReporter.format_opportunity(ticker, action, side, price_cents, reason, weather_context)
        self._write(message)

    def trade_executed(self, ticker: str, action: str, side: str, price_cents: int, order_id: str) -> None:
        message = TradeReporter.format_trade_executed(ticker, action, side, price_cents, order_id)
        self._write(message)

    def trade_failed(self, ticker: str, reason: str) -> None:
        message = TradeReporter.format_trade_failed(ticker, reason)
        self._write(message)

    def insufficient_balance(self, ticker: str, required_cents: int, available_cents: int) -> None:
        message = TradeReporter.format_insufficient_balance(ticker, required_cents, available_cents)
        self._write(message)

    def balance_updated(self, old_balance_cents: int, new_balance_cents: int) -> None:
        message = TradeReporter.format_balance_updated(old_balance_cents, new_balance_cents)
        self._write(message)


class _LifecycleStatusHelper:
    def __init__(self, writer_write):
        self._write = writer_write

    def waiting_for_next_scan(self, seconds: int) -> None:
        message = TimeFormatter.waiting_for_next_scan(seconds)
        self._write(message)

    def error_occurred(self, error_message: str) -> None:
        self._write(MessageFormatter.error_occurred(error_message))

    def initialization_complete(self) -> None:
        self._write(MessageFormatter.initialization_complete())

    def shutdown_complete(self) -> None:
        self._write(MessageFormatter.shutdown_complete())


class StatusReporter:
    """
    Provides human-readable status reporting for trading operations.
    Outputs clean status messages without timestamps or logger prefixes.
    """

    def __init__(self, output_stream=None):
        self._writer = OutputWriter(output_stream)
        from .time_utils import get_current_utc

        self.session_start_time = get_current_utc()

        self._helpers = (
            _MarketStatusHelper(self._writer.write),
            _TradeStatusHelper(self._writer.write),
            _LifecycleStatusHelper(self._writer.write),
        )

    def __getattr__(self, name):
        for helper in self._helpers:
            try:
                return getattr(helper, name)
            except AttributeError:  # Expected when helper doesn't have the method  # policy_guard: allow-silent-handler
                continue
        raise AttributeError(f"{self.__class__.__name__} has no attribute {name}")

    def print_status(self, message: str) -> None:
        self._writer.write(message)


# Global instance for easy access
status_reporter = StatusReporter()
