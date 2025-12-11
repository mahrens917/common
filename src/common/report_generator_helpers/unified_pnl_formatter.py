"""
Unified P&L section formatter.

Formats simplified P&L sections using current market values.
"""

from typing import List

from .dollar_converter import DollarConverter
from .pnl_emoji_selector import PnLEmojiSelector
from .statistics_calculator import StatisticsCalculator


class UnifiedPnLFormatter:
    """Formats simplified P&L sections with unified P&L calculation."""

    def __init__(
        self,
        emoji_selector: PnLEmojiSelector,
        dollar_converter: DollarConverter,
        stats_calculator: StatisticsCalculator,
    ):
        """
        Initialize unified P&L formatter.

        Args:
            emoji_selector: Emoji selector for P&L indicators
            dollar_converter: Dollar converter for calculations
            stats_calculator: Statistics calculator for metrics
        """
        self.emoji_selector = emoji_selector
        self.dollar_converter = dollar_converter
        self.stats_calculator = stats_calculator

    def format_unified_pnl_section(self, period_name: str, total_pnl_cents: int, trade_count: int, trades: List) -> str:
        """
        Format a simplified P&L section with unified P&L.

        Args:
            period_name: Display name for the period
            total_pnl_cents: Total P&L in cents (market value based)
            trade_count: Number of trades
            trades: List of trade records for calculations

        Returns:
            Formatted section string
        """
        total_pnl_dollars = total_pnl_cents / 100

        # Calculate totals from trades
        total_contracts = self.dollar_converter.calculate_total_contracts(trades)
        total_cost_dollars = self.dollar_converter.calculate_total_cost_dollars(trades)

        # Calculate win rate using current market values
        win_rate = self.stats_calculator.calculate_win_rate(trades)

        # Select emoji
        pnl_emoji = self.emoji_selector.get_fire_or_cold_emoji(total_pnl_dollars)

        lines = [f"{pnl_emoji} **{period_name}**"]
        lines.append(f"├── P&L: ${total_pnl_dollars:+,.2f} ({len(trades)} trades)")
        lines.append(f"├── Contracts Traded: {total_contracts:,}")
        lines.append(f"├── Money Traded: ${total_cost_dollars:,.2f}")

        # Total P&L with percentage
        if total_cost_dollars > 0:
            pnl_percentage = (total_pnl_dollars / total_cost_dollars) * 100
            lines.append(f"├── Total P&L (%): ${total_pnl_dollars:+,.2f} ({pnl_percentage:+.1f}%)")
        else:
            lines.append(f"├── Total P&L (%): ${total_pnl_dollars:+,.2f}")

        # Win Rate
        lines.append(f"└── Win Rate: {win_rate:.0%} ({len(trades)} trades)")

        return "\n".join(lines)
