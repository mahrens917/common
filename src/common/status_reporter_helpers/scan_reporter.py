"""Scanning and opportunity summary reporting functionality."""

from .base_reporter import WriterBackedReporter
from .message_formatter import MessageFormatter
from .summary_builder import SummaryBuilder
from .time_formatter import TimeFormatter


class ScanReporter(WriterBackedReporter):
    """Handles scan-related status reporting."""

    def scanning_markets(self, market_count: int) -> None:
        """Report that we're scanning markets for opportunities."""
        self._writer.write(MessageFormatter.scanning_markets(market_count))

    def opportunities_summary(self, opportunities_found: int, trades_executed: int, markets_closed: int = 0) -> None:
        """
        Report a summary of opportunities found and trades executed.

        Args:
            opportunities_found: Number of trading opportunities identified
            trades_executed: Number of trades successfully executed
            markets_closed: Number of markets that were closed/expired
        """
        message = SummaryBuilder.build_opportunities_summary(opportunities_found, trades_executed, markets_closed)
        self._writer.write(message)

    def waiting_for_next_scan(self, seconds: int) -> None:
        """Report that we're waiting for the next scan cycle."""
        message = TimeFormatter.waiting_for_next_scan(seconds)
        self._writer.write(message)
