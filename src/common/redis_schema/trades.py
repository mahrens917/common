from __future__ import annotations

"""Trade-related Redis key helpers."""


from dataclasses import dataclass
from datetime import date

from common.exceptions import ValidationError

from .namespaces import KeyBuilder, RedisNamespace, sanitize_segment
from .validators import register_namespace

register_namespace("trades:record:", "Stored trade records keyed by date/order")
register_namespace("trades:index:", "Trade indices (by station, rule, etc.)")
register_namespace("trades:summary:", "Aggregated trade/P&L summaries")


@dataclass(frozen=True)
class TradeRecordKey:
    """Key pointing to a serialized trade record."""

    trade_date: date
    order_id: str

    def key(self) -> str:
        try:
            order_segment = sanitize_segment(self.order_id)
        except ValidationError as exc:  # policy_guard: allow-silent-handler
            raise ValueError(str(exc)) from exc
        segments = ["record", self.trade_date.isoformat(), order_segment]
        builder = KeyBuilder(RedisNamespace.TRADES, tuple(segments))
        return builder.render()


@dataclass(frozen=True)
class TradeIndexKey:
    """Key for secondary trade indices (sets)."""

    index_type: str
    value: str

    def key(self) -> str:
        segments = ["index", sanitize_segment(self.index_type), sanitize_segment(self.value)]
        builder = KeyBuilder(RedisNamespace.TRADES, tuple(segments))
        return builder.render()


@dataclass(frozen=True)
class TradeSummaryKey:
    """Key storing aggregated trade metrics for a date."""

    trade_date: date

    def key(self) -> str:
        segments = ["summary", self.trade_date.isoformat()]
        builder = KeyBuilder(RedisNamespace.TRADES, tuple(segments))
        return builder.render()
