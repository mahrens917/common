"""
Current day report formatter.

Formats current day reports with unrealized P&L.
"""

from ..data_models.trade_record import PnLReport
from .pnl_emoji_selector import PnLEmojiSelector
from .rule_breakdown_formatter import RuleBreakdownFormatter
from .station_breakdown_formatter import StationBreakdownFormatter


class CurrentDayFormatter:
    """Formats current day reports with unrealized P&L."""

    def __init__(
        self,
        emoji_selector: PnLEmojiSelector,
        station_formatter: StationBreakdownFormatter,
        rule_formatter: RuleBreakdownFormatter,
    ):
        """
        Initialize current day formatter.

        Args:
            emoji_selector: Emoji selector for P&L indicators
            station_formatter: Station breakdown formatter
            rule_formatter: Rule breakdown formatter
        """
        self.emoji_selector = emoji_selector
        self.station_formatter = station_formatter
        self.rule_formatter = rule_formatter

    def format_current_day_report(self, report: PnLReport, unrealized_pnl_cents: int, date_str: str) -> str:
        """
        Format current day report with unrealized P&L.

        Args:
            report: P&L report data
            unrealized_pnl_cents: Unrealized P&L in cents
            date_str: Formatted date string for display

        Returns:
            Formatted report string
        """
        # Convert cents to dollars for display
        total_pnl_dollars = report.total_pnl_cents / 100
        total_cost_dollars = report.total_cost_cents / 100
        total_return_dollars = (report.total_cost_cents + report.total_pnl_cents) / 100
        unrealized_dollars = unrealized_pnl_cents / 100

        # Determine P&L emoji
        pnl_emoji = self.emoji_selector.get_pnl_emoji(total_pnl_dollars)

        # Build main report with unrealized P&L integrated
        lines = [
            f"📊 **Today's Report - {date_str}**",
            "",
            f"{pnl_emoji} **Total: Put up ${total_cost_dollars:,.2f}, "
            f"Got back ${total_return_dollars:,.2f}, P&L ${total_pnl_dollars:+,.2f}**",
            f"📈 Total Trades: {report.total_trades:,}",
            f"🎯 Win Rate: {report.win_rate:.1%}",
            "",
            f"💰 **P&L Breakdown:**",
            f"📊 P&L: ${total_pnl_dollars:+,.2f} ({report.total_trades:,} trades)",
            f"🔄 Unrealized P&L: ${unrealized_dollars:+,.2f} (market-based pricing)",
        ]

        # Add weather station breakdown
        lines.extend(self.station_formatter.format_station_breakdown(report.by_weather_station))

        # Add trading rule breakdown
        lines.extend(self.rule_formatter.format_rule_breakdown(report.by_rule))

        return "\n".join(lines)
