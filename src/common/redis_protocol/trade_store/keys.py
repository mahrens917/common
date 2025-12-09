"""
Key builders for the trade store domain.

The helpers centralise Redis key construction so the calling code can focus on
behaviour and the keys remain easy to audit when additional indices are added.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TradeKeyBuilder:
    """Utility responsible for building Redis keys for trade data."""

    trade_prefix: str = "trades"
    order_index_prefix: str = "order_id_index"
    order_metadata_prefix: str = "order_metadata"
    unrealized_prefix: str = "pnl:unrealized"

    def trade(self, trade_date: date, order_id: str) -> str:
        """Key for the canonical trade payload."""
        return f"{self.trade_prefix}:{trade_date.isoformat()}:{order_id}"

    def station(self, station: str) -> str:
        """Key for the weather station trade index."""
        return f"{self.trade_prefix}:by_station:{station}"

    def rule(self, rule: str) -> str:
        """Key for the trading rule index."""
        return f"{self.trade_prefix}:by_rule:{rule}"

    def category(self, category: str) -> str:
        """Key for the market category index."""
        return f"{self.trade_prefix}:by_category:{category}"

    def date_index(self, trade_date: date) -> str:
        """Key for the trade IDs associated with a given date."""
        return f"{self.trade_prefix}:by_date:{trade_date.isoformat()}"

    def daily_summary(self, trade_date: date) -> str:
        """Key for daily P&L summary snapshots."""
        return f"{self.trade_prefix}:daily_summary:{trade_date.isoformat()}"

    def order_index(self, order_id: str) -> str:
        """Key used to locate the primary trade entry from an order id."""
        return f"{self.order_index_prefix}:{order_id}"

    def order_metadata(self, order_id: str) -> str:
        """Key for order metadata captured before a fill is processed."""
        return f"{self.order_metadata_prefix}:{order_id}"

    def unrealized_pnl(self, trade_date: date) -> str:
        """Key for unrealized P&L snapshots."""
        return f"{self.unrealized_prefix}:{trade_date.isoformat()}"
