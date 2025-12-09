"""
Rule breakdown formatter for trading rule P&L sections.

Formats trading rule breakdown sections with cost, return, and P&L details.
"""

from typing import Dict, List

from ..data_models.trade_record import PnLBreakdown
from .pnl_emoji_selector import PnLEmojiSelector


class RuleBreakdownFormatter:
    """Formats trading rule breakdown sections."""

    def __init__(self, emoji_selector: PnLEmojiSelector):
        """
        Initialize rule breakdown formatter.

        Args:
            emoji_selector: Emoji selector for P&L indicators
        """
        self.emoji_selector = emoji_selector

    def format_rule_breakdown(self, by_rule: Dict[str, PnLBreakdown]) -> List[str]:
        """
        Format trading rule breakdown section.

        Args:
            by_rule: Rule breakdown dictionary

        Returns:
            List of formatted lines
        """
        if not by_rule:
            return []

        lines = ["", "📋 **By Trading Rule:**"]

        for rule in sorted(by_rule.keys()):
            breakdown = by_rule[rule]
            rule_pnl = breakdown.pnl_cents / 100
            rule_cost = breakdown.cost_cents / 100
            rule_return = (breakdown.cost_cents + breakdown.pnl_cents) / 100

            rule_emoji = self.emoji_selector.get_pnl_emoji(rule_pnl)
            rule_display = rule.replace("_", " ").title()

            lines.append(
                f"  {rule_emoji} {rule_display}: Put up ${rule_cost:,.2f}, "
                f"Got back ${rule_return:,.2f}, P&L ${rule_pnl:+,.2f} "
                f"({breakdown.trades_count:,} trades, {breakdown.win_rate:.1%} win)"
            )

        return lines
