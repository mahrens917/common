"""Reporter for trade execution and balance messages."""


class TradeReporter:
    """Formats trade execution, failure, and balance update messages."""

    @staticmethod
    def format_trade_executed(
        ticker: str, action: str, side: str, price_cents: int, order_id: str
    ) -> str:
        """Format trade execution success message."""
        price_dollars = price_cents / 100
        return (
            f"✅ Trade executed: {action} {side} {ticker} @ "
            f"${price_dollars:.2f} (Order: {order_id})"
        )

    @staticmethod
    def format_trade_failed(ticker: str, reason: str) -> str:
        """Format trade failure message."""
        return f"❌ Trade failed for {ticker}: {reason}"

    @staticmethod
    def format_insufficient_balance(ticker: str, required_cents: int, available_cents: int) -> str:
        """Format insufficient balance message."""
        required_dollars = required_cents / 100
        available_dollars = available_cents / 100
        return (
            f"💸 Insufficient balance for {ticker}: "
            f"need ${required_dollars:.2f}, have ${available_dollars:.2f}"
        )

    @staticmethod
    def format_balance_updated(old_balance_cents: int, new_balance_cents: int) -> str:
        """Format balance update message."""
        old_dollars = old_balance_cents / 100
        new_dollars = new_balance_cents / 100
        change_dollars = (new_balance_cents - old_balance_cents) / 100

        change_sign = "+" if change_dollars >= 0 else ""

        return (
            f"💰 Balance updated: ${old_dollars:.2f} → ${new_dollars:.2f} "
            f"({change_sign}${change_dollars:.2f})"
        )
