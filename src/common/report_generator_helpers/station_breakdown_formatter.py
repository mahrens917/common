"""
Station breakdown formatter for weather station P&L sections.

Formats weather station breakdown sections with cost, return, and P&L details.
"""

from typing import Dict, List

from ..data_models.trade_record import PnLBreakdown
from .pnl_emoji_selector import PnLEmojiSelector


class StationBreakdownFormatter:
    """Formats weather station breakdown sections."""

    def __init__(self, emoji_selector: PnLEmojiSelector):
        """
        Initialize station breakdown formatter.

        Args:
            emoji_selector: Emoji selector for P&L indicators
        """
        self.emoji_selector = emoji_selector

    def format_station_breakdown(self, by_weather_station: Dict[str, PnLBreakdown]) -> List[str]:
        """
        Format weather station breakdown section.

        Args:
            by_weather_station: Station breakdown dictionary

        Returns:
            List of formatted lines
        """
        if not by_weather_station:
            return []

        lines = ["", "🏛️ **By Weather Station:**"]

        for station, breakdown in sorted(by_weather_station.items()):
            station_pnl = breakdown.pnl_cents / 100
            station_cost = breakdown.cost_cents / 100
            station_return = (breakdown.cost_cents + breakdown.pnl_cents) / 100

            station_emoji = self.emoji_selector.get_pnl_emoji(station_pnl)

            lines.append(
                f"  {station_emoji} {station}: Put up ${station_cost:,.2f}, "
                f"Got back ${station_return:,.2f}, P&L ${station_pnl:+,.2f} "
                f"({breakdown.trades_count:,} trades, {breakdown.win_rate:.1%} win)"
            )

        return lines
