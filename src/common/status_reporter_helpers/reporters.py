"""Reporter classes that combine formatting with output writing."""

from __future__ import annotations

import sys
from typing import Optional

from . import formatters


class OutputWriter:
    """Handles writing status messages to output stream."""

    def __init__(self, output_stream=None):
        self.output_stream = output_stream or sys.stdout

    def write(self, message: str) -> None:
        """Write a status message to the output stream."""
        try:
            print(message, file=self.output_stream, flush=True)
        except (BrokenPipeError, OSError):  # Best-effort cleanup operation  # policy_guard: allow-silent-handler
            pass


class WriterBackedReporter:
    """Provides a writer-backed reporter initialization."""

    def __init__(self, writer):
        self._writer = writer


class MarketReporter(WriterBackedReporter):
    """Handles market-related status reporting."""

    def tracking_started(self) -> None:
        self._writer.write(formatters.tracking_started())

    def markets_closed(self) -> None:
        self._writer.write(formatters.markets_closed())

    def markets_open(self) -> None:
        self._writer.write(formatters.markets_open())

    def checking_market_hours(self) -> None:
        self._writer.write(formatters.checking_market_hours())


class LifecycleReporter(WriterBackedReporter):
    """Handles lifecycle and error status reporting."""

    def error_occurred(self, error_message: str) -> None:
        self._writer.write(formatters.error_occurred(error_message))

    def initialization_complete(self) -> None:
        self._writer.write(formatters.initialization_complete())

    def shutdown_complete(self) -> None:
        self._writer.write(formatters.shutdown_complete())


class ScanReporter(WriterBackedReporter):
    """Handles scan-related status reporting."""

    def scanning_markets(self, market_count: int) -> None:
        self._writer.write(formatters.scanning_markets(market_count))

    def opportunities_summary(self, opportunities_found: int, trades_executed: int, markets_closed: int = 0) -> None:
        message = formatters.build_opportunities_summary(opportunities_found, trades_executed, markets_closed)
        self._writer.write(message)

    def waiting_for_next_scan(self, seconds: int) -> None:
        message = formatters.waiting_for_next_scan(seconds)
        self._writer.write(message)


class TradeStatusReporter(WriterBackedReporter):
    """Handles trade-related status reporting."""

    def trade_opportunity_found(
        self,
        ticker: str,
        action: str,
        side: str,
        price_cents: int,
        reason: str,
        weather_context: Optional[str] = None,
    ) -> None:
        message = formatters.format_opportunity(ticker, action, side, price_cents, reason, weather_context)
        self._writer.write(message)

    def trade_executed(self, ticker: str, action: str, side: str, price_cents: int, order_id: str) -> None:
        message = formatters.format_trade_executed(ticker, action, side, price_cents, order_id)
        self._writer.write(message)

    def trade_failed(self, ticker: str, reason: str) -> None:
        message = formatters.format_trade_failed(ticker, reason)
        self._writer.write(message)

    def insufficient_balance(self, ticker: str, required_cents: int, available_cents: int) -> None:
        message = formatters.format_insufficient_balance(ticker, required_cents, available_cents)
        self._writer.write(message)

    def balance_updated(self, old_balance_cents: int, new_balance_cents: int) -> None:
        message = formatters.format_balance_updated(old_balance_cents, new_balance_cents)
        self._writer.write(message)
