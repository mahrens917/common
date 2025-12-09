"""
P&L emoji selector for visual indicators.

Selects appropriate emoji based on P&L values for Telegram reports.
"""


class PnLEmojiSelector:
    """Selects appropriate emoji based on P&L values."""

    @staticmethod
    def get_pnl_emoji(pnl_dollars: float) -> str:
        """
        Get emoji indicator for P&L value.

        Args:
            pnl_dollars: P&L value in dollars

        Returns:
            Emoji string (📈 for positive, 📉 for negative)
        """
        return "📈" if pnl_dollars >= 0 else "📉"

    @staticmethod
    def get_fire_or_cold_emoji(pnl_dollars: float) -> str:
        """
        Get fire/cold emoji for P&L value.

        Args:
            pnl_dollars: P&L value in dollars

        Returns:
            Emoji string (🔥 for positive, ❄️ for negative)
        """
        return "🔥" if pnl_dollars >= 0 else "❄️"
