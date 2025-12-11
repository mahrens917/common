"""
Time period section formatter for unified P&L reports.

Formats standardized time period sections with tree-style display.
"""

from typing import List, Optional

from ..data_models.trade_record import PnLReport
from .dollar_converter import DollarConverter
from .pnl_emoji_selector import PnLEmojiSelector


class TimePeriodFormatter:
    """Formats time period sections for unified P&L reports."""

    def __init__(self, emoji_selector: PnLEmojiSelector, dollar_converter: DollarConverter):
        """
        Initialize time period formatter.

        Args:
            emoji_selector: Emoji selector for P&L indicators
            dollar_converter: Dollar converter for calculations
        """
        self.emoji_selector = emoji_selector
        self.dollar_converter = dollar_converter

    def format_time_period_section(
        self,
        report: PnLReport,
        period_name: str,
        include_unrealized: bool = False,
        unrealized_pnl_cents: int = 0,
        days_count: Optional[int] = None,
        trades: Optional[List] = None,
    ) -> str:
        """
        Format a standardized time period section.

        Args:
            report: P&L report data
            period_name: Display name for the period
            include_unrealized: Whether to include unrealized P&L
            unrealized_pnl_cents: Unrealized P&L in cents
            days_count: Number of days for average calculation
            trades: Optional list of actual trade records

        Returns:
            Formatted section string
        """
        total_pnl_dollars = report.total_pnl_cents / 100
        total_cost_dollars = report.total_cost_cents / 100
        unrealized_dollars = unrealized_pnl_cents / 100

        # Calculate total contracts and cost from trade data
        total_contracts = self.dollar_converter.calculate_total_contracts(trades)

        # Determine total P&L with unrealized
        unrealized_component = unrealized_dollars if include_unrealized else 0
        total_with_unrealized = total_pnl_dollars + unrealized_component

        # Select emoji
        pnl_emoji = self.emoji_selector.get_fire_or_cold_emoji(total_with_unrealized)

        lines = [f"{pnl_emoji} **{period_name}**"]
        lines.append(f"├── P&L: ${total_pnl_dollars:+,.2f} ({report.total_trades} trades)")

        if include_unrealized:
            lines.append(f"├── Unrealized P&L: ${unrealized_dollars:+,.2f} (market-based)")

        lines.append(f"├── Contracts Traded: {total_contracts:,}")
        lines.append(f"├── Money Traded: ${total_cost_dollars:,.2f}")

        # Total P&L with percentage
        if total_cost_dollars > 0:
            pnl_percentage = (total_with_unrealized / total_cost_dollars) * 100
            lines.append(f"├── Total P&L (%): ${total_with_unrealized:+,.2f} ({pnl_percentage:+.1f}%)")
        else:
            lines.append(f"├── Total P&L (%): ${total_with_unrealized:+,.2f}")

        lines.append(f"├── Win Rate: {report.win_rate:.0%} ({report.total_trades} trades)")

        # Daily average for 7-day and 30-day periods
        if days_count:
            daily_avg_absolute = total_pnl_dollars / days_count
            daily_avg_percent = (daily_avg_absolute / total_cost_dollars) * 100 if total_cost_dollars > 0 else 0
            lines.append(f"└── Daily Avg: ${daily_avg_absolute:+,.2f} ({daily_avg_percent:+.1f}%)")
        else:
            # Make last item the end for today/yesterday
            lines[-1] = lines[-1].replace("├──", "└──")

        return "\n".join(lines)
