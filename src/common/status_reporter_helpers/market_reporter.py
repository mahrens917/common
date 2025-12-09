"""Market status reporting functionality."""

from .base_reporter import WriterBackedReporter
from .message_formatter import MessageFormatter


class MarketReporter(WriterBackedReporter):
    """Handles market-related status reporting."""

    def tracking_started(self) -> None:
        """Report that tracking has started."""
        self._writer.write(MessageFormatter.tracking_started())

    def markets_closed(self) -> None:
        """Report that markets are closed."""
        self._writer.write(MessageFormatter.markets_closed())

    def markets_open(self) -> None:
        """Report that markets are open."""
        self._writer.write(MessageFormatter.markets_open())

    def checking_market_hours(self) -> None:
        """Report that we're checking market hours."""
        self._writer.write(MessageFormatter.checking_market_hours())
