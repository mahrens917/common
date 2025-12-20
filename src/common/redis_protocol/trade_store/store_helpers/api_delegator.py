"""API delegation for TradeStore public methods."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from common.truthy import pick_truthy

from ....data_models.trade_record import PnLReport, TradeRecord
from .api_delegator_helpers import PnLDelegator, QueryDelegator, TradeDelegator

_DEFAULT_MARKET_CATEGORY = "weather"


class TradeStoreAPIDelegator:
    """Delegate TradeStore public API to internal components."""

    def __init__(self, repository, metadata_store, queries, pnl, price_updater, executor, deps):
        self._trade_delegator = TradeDelegator(repository, metadata_store, executor, deps, price_updater)
        self._query_delegator = QueryDelegator(queries, executor)
        self._pnl_delegator = PnLDelegator(pnl, executor)

    async def store_trade(self, trade: TradeRecord) -> bool:
        return await self._trade_delegator.store_trade(trade)

    async def mark_trade_settled(self, order_id: str, settlement_price_cents: int, settled_at: Optional[datetime] = None) -> bool:
        return await self._trade_delegator.mark_trade_settled(order_id, settlement_price_cents, settled_at)

    async def get_trade(self, trade_date: date, order_id: str) -> Optional[TradeRecord]:
        return await self._trade_delegator.get_trade(trade_date, order_id)

    async def get_trade_by_order_id(self, order_id: str) -> Optional[TradeRecord]:
        return await self._trade_delegator.get_trade_by_order_id(order_id)

    async def store_order_metadata(
        self,
        order_id: str,
        trade_rule: str,
        trade_reason: str,
        *,
        market_category: Optional[str] = None,
        weather_station: Optional[str] = None,
    ) -> bool:
        resolved_market_category = market_category if market_category is not None else _DEFAULT_MARKET_CATEGORY
        return await self._trade_delegator.store_order_metadata(
            order_id,
            trade_rule,
            trade_reason,
            market_category=resolved_market_category,
            weather_station=weather_station,
        )

    async def get_order_metadata(self, order_id: str) -> Optional[Dict[str, str]]:
        return await self._trade_delegator.get_order_metadata(order_id)

    async def get_trades_by_date_range(self, start_date: date, end_date: date) -> list[TradeRecord]:
        return await self._query_delegator.get_trades_by_date_range(start_date, end_date)

    async def get_trades_by_station(self, station: str) -> list[TradeRecord]:
        return await self._query_delegator.get_trades_by_station(station)

    async def get_trades_by_rule(self, rule: str) -> list[TradeRecord]:
        return await self._query_delegator.get_trades_by_rule(rule)

    async def get_trades_closed_today(self) -> list[TradeRecord]:
        return await self._query_delegator.get_trades_closed_today()

    async def get_trades_closed_yesterday(self) -> list[TradeRecord]:
        return await self._query_delegator.get_trades_closed_yesterday()

    async def get_unrealized_trades_for_date(self, target_date: date) -> list[TradeRecord]:
        return await self._query_delegator.get_unrealized_trades_for_date(target_date)

    async def store_daily_summary(self, summary: PnLReport) -> bool:
        return await self._pnl_delegator.store_daily_summary(summary)

    async def get_daily_summary(self, trade_date: date) -> Optional[Dict[str, Any]]:
        return await self._pnl_delegator.get_daily_summary(trade_date)

    async def store_unrealized_pnl_data(self, redis_key: str, data: Dict[str, Any]) -> bool:
        return await self._pnl_delegator.store_unrealized_pnl_data(redis_key, data)

    async def get_unrealized_pnl_data(self, redis_key: str) -> Optional[Dict[str, Any]]:
        return await self._pnl_delegator.get_unrealized_pnl_data(redis_key)

    async def get_unrealized_pnl_history(self, start_date: date, end_date: date) -> list[Dict[str, Any]]:
        return await self._pnl_delegator.get_unrealized_pnl_history(start_date, end_date)

    async def update_trade_prices(self, market_ticker: str, yes_bid: float, yes_ask: float) -> int:
        return await self._trade_delegator.update_trade_prices(market_ticker, yes_bid, yes_ask)
