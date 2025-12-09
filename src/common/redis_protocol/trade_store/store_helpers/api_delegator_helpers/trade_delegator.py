"""Trade record operations delegation"""

from datetime import date, datetime
from typing import Dict, Optional

from .....data_models.trade_record import TradeRecord


class TradeDelegator:
    """Delegates trade record and metadata operations"""

    def __init__(self, repository, metadata_store, executor, deps, price_updater):
        """
        Initialize trade delegator

        Args:
            repository: TradeRecordRepository instance
            metadata_store: OrderMetadataStore instance
            executor: Executor for Redis guard operations
            deps: Dependencies provider
            price_updater: TradePriceUpdater instance
        """
        self._repository = repository
        self._metadata_store = metadata_store
        self._executor = executor
        self._deps = deps
        self._price_updater = price_updater

    async def store_trade(self, trade: TradeRecord) -> bool:
        """Store a trade record"""
        return await self._executor.run_with_redis_guard(
            "store_trade", lambda: self._repository.store(trade)
        )

    async def mark_trade_settled(
        self, order_id: str, settlement_price_cents: int, settled_at: Optional[datetime] = None
    ) -> bool:
        """Mark a trade as settled"""
        return await self._executor.run_with_redis_guard(
            "mark_trade_settled",
            lambda: self._repository.mark_settled(
                order_id,
                settlement_price_cents=settlement_price_cents,
                settled_at=settled_at,
                timestamp_provider=self._deps.get_timestamp_provider(),
            ),
        )

    async def get_trade(self, trade_date: date, order_id: str) -> Optional[TradeRecord]:
        """Get a trade by date and order ID"""
        return await self._executor.run_with_redis_guard(
            "get_trade", lambda: self._repository.get(trade_date, order_id)
        )

    async def get_trade_by_order_id(self, order_id: str) -> Optional[TradeRecord]:
        """Get a trade by order ID only"""
        return await self._executor.run_with_redis_guard(
            "get_trade_by_order_id", lambda: self._repository.get_by_order_id(order_id)
        )

    async def store_order_metadata(
        self,
        order_id: str,
        trade_rule: str,
        trade_reason: str,
        *,
        market_category: str = "weather",
        weather_station: Optional[str] = None,
    ) -> bool:
        """Store order metadata"""
        return await self._executor.run_with_redis_guard(
            "store_order_metadata",
            lambda: self._metadata_store.store(
                order_id,
                trade_rule=trade_rule,
                trade_reason=trade_reason,
                market_category=market_category,
                weather_station=weather_station,
            ),
        )

    async def get_order_metadata(self, order_id: str) -> Optional[Dict[str, str]]:
        """Get order metadata"""

        return await self._executor.run_with_redis_guard(
            "get_order_metadata", lambda: self._metadata_store.load(order_id)
        )

    async def update_trade_prices(self, market_ticker: str, yes_bid: float, yes_ask: float) -> int:
        """Update trade prices for a market"""
        return await self._executor.run_with_redis_guard(
            "update_trade_prices",
            lambda: self._price_updater.update_market_prices(
                market_ticker, yes_bid=yes_bid, yes_ask=yes_ask
            ),
        )
