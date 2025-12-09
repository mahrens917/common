"""Trade status reporting functionality."""

from typing import Optional

from .base_reporter import WriterBackedReporter
from .opportunity_reporter import OpportunityReporter
from .trade_reporter import TradeReporter


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
        """Report that a trading opportunity was found."""
        message = OpportunityReporter.format_opportunity(
            ticker, action, side, price_cents, reason, weather_context
        )
        self._writer.write(message)

    def trade_executed(
        self, ticker: str, action: str, side: str, price_cents: int, order_id: str
    ) -> None:
        """Report that a trade was successfully executed."""
        message = TradeReporter.format_trade_executed(ticker, action, side, price_cents, order_id)
        self._writer.write(message)

    def trade_failed(self, ticker: str, reason: str) -> None:
        """Report that a trade failed to execute."""
        message = TradeReporter.format_trade_failed(ticker, reason)
        self._writer.write(message)

    def insufficient_balance(self, ticker: str, required_cents: int, available_cents: int) -> None:
        """Report insufficient balance for a trade."""
        message = TradeReporter.format_insufficient_balance(ticker, required_cents, available_cents)
        self._writer.write(message)

    def balance_updated(self, old_balance_cents: int, new_balance_cents: int) -> None:
        """Report that account balance was updated."""
        message = TradeReporter.format_balance_updated(old_balance_cents, new_balance_cents)
        self._writer.write(message)
