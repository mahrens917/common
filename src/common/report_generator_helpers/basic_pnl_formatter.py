"""
Basic P&L report formatter.

Formats standard P&L reports with station and rule breakdowns.
"""

from ..data_models.trade_record import PnLReport
from .pnl_emoji_selector import PnLEmojiSelector
from .rule_breakdown_formatter import RuleBreakdownFormatter
from .station_breakdown_formatter import StationBreakdownFormatter


class BasicPnLFormatter:
    """Formats basic P&L reports."""

    def __init__(
        self,
        emoji_selector: PnLEmojiSelector,
        station_formatter: StationBreakdownFormatter,
        rule_formatter: RuleBreakdownFormatter,
    ):
        """
        Initialize basic P&L formatter.

        Args:
            emoji_selector: Emoji selector for P&L indicators
            station_formatter: Station breakdown formatter
            rule_formatter: Rule breakdown formatter
        """
        self.emoji_selector = emoji_selector
        self.station_formatter = station_formatter
        self.rule_formatter = rule_formatter

    def format_pnl_report(self, report: PnLReport, title: str) -> str:
        """
        Format a P&L report for Telegram display.

        Args:
            report: P&L report data
            title: Report title

        Returns:
            Formatted report string
        """
        # Convert cents to dollars for display
        total_pnl_dollars = report.total_pnl_cents / 100
        total_cost_dollars = report.total_cost_cents / 100

        # Determine P&L emoji
        pnl_emoji = self.emoji_selector.get_pnl_emoji(total_pnl_dollars)

        # Calculate total return (cost + pnl)
        total_return_dollars = (report.total_cost_cents + report.total_pnl_cents) / 100

        # Build main report
        lines = [
            f"📊 **{title}**",
            "",
            f"{pnl_emoji} **Total: Put up ${total_cost_dollars:,.2f}, "
            f"Got back ${total_return_dollars:,.2f}, P&L ${total_pnl_dollars:+,.2f}**",
            f"📈 Total Trades: {report.total_trades:,}",
            f"🎯 Win Rate: {report.win_rate:.1%}",
            "",
            f"💰 **P&L Breakdown:**",
            f"📊 P&L: ${total_pnl_dollars:+,.2f} ({report.total_trades:,} trades)",
        ]

        # Add weather station breakdown
        lines.extend(self.station_formatter.format_station_breakdown(report.by_weather_station))

        # Add trading rule breakdown
        lines.extend(self.rule_formatter.format_rule_breakdown(report.by_rule))

        return "\n".join(lines)
