"""
Redis protocol for Kalshi trade data storage and retrieval.

The TradeStore composes dedicated components for persistence, aggregation,
metadata, and pricing concerns. The orchestration layer focuses on connection
management and fail-fast wiring, keeping each responsibility discoverable.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from redis.asyncio import Redis

from ..typing import RedisClient
from .dependencies_factory import TradeStoreDependencies, create_dependencies
from .errors import OrderMetadataError, TradeStoreError, TradeStoreShutdownError

ORIGINAL_REDIS_CLASS = Redis

logger = logging.getLogger(__name__)

_DEFAULT_MARKET_CATEGORY = "weather"


class TradeStore:
    """
    Redis-backed store for Kalshi trade data.

    TradeStore composes several internal services so each domain surface can be
    exercised independently whilst sharing the same Redis connection manager.
    """

    def __init__(
        self,
        redis: Optional[RedisClient] = None,
        *,
        dependencies: Optional[TradeStoreDependencies] = None,
    ) -> None:
        self.logger = logger
        deps = dependencies or create_dependencies(self.logger, redis, self._get_redis)
        self._base_connection = deps.base_connection
        self._connection_mgr = deps.connection_mgr
        self._pool_acquirer = deps.pool_acquirer
        self._executor = deps.executor
        self._deps = deps.deps
        self.timezone = deps.timezone
        self._keys = deps.keys
        self._codec = deps.codec
        self._repository = deps.repository
        self._metadata_store = deps.metadata_store
        self._queries = deps.queries
        self._pnl = deps.pnl
        self._price_updater = deps.price_updater

    async def _get_redis(self) -> RedisClient:
        """Get Redis client with automatic reconnection."""
        return await self._connection_mgr.get_redis(lambda: self.redis)

    async def initialize(self) -> bool:
        """Initialize Redis connection."""

        async def _acquire_pool(allow_reuse: bool):
            return await self._pool_acquirer.acquire_pool(
                allow_reuse=allow_reuse,
                redis_getter=lambda: self.redis,
                redis_setter=lambda v: setattr(self, "_redis_client", v),
                original_redis_class=ORIGINAL_REDIS_CLASS,
            )

        return await self._connection_mgr.initialize(
            redis_setter=lambda v: setattr(self, "_redis_client", v),
            settings_resolver=self._connection_mgr.resolve_connection_settings,
            pool_acquirer=_acquire_pool,
        )

    async def close(self) -> None:
        """Close Redis connection cleanly."""
        await self._connection_mgr.close(redis_setter=lambda v: setattr(self, "_redis_client", v))

    @property
    def redis(self) -> Optional[Redis]:
        """Get current Redis client."""
        return getattr(self, "_redis_client", self._connection_mgr.redis)

    @redis.setter
    def redis(self, value: Optional[Redis]) -> None:
        """Set Redis client."""
        self._redis_client = value
        self._connection_mgr.redis = value

    async def store_trade(self, trade: Any) -> bool:
        return await self._executor.run_with_redis_guard("store_trade", lambda: self._repository.store(trade))

    async def mark_trade_settled(self, order_id: str, settlement_price_cents: int, settled_at: Optional[datetime] = None) -> bool:
        return await self._executor.run_with_redis_guard(
            "mark_trade_settled",
            lambda: self._repository.mark_settled(
                order_id,
                settlement_price_cents=settlement_price_cents,
                settled_at=settled_at,
                timestamp_provider=self._deps.get_timestamp_provider(),
            ),
        )

    async def get_trade(self, trade_date: date, order_id: str) -> Any:
        return await self._executor.run_with_redis_guard("get_trade", lambda: self._repository.get(trade_date, order_id))

    async def get_trade_by_order_id(self, order_id: str) -> Any:
        return await self._executor.run_with_redis_guard("get_trade_by_order_id", lambda: self._repository.get_by_order_id(order_id))

    async def store_order_metadata(
        self,
        order_id: str,
        trade_rule: str,
        trade_reason: str,
        *,
        market_category: Optional[str] = None,
        weather_station: Optional[str] = None,
    ) -> bool:
        resolved = market_category if market_category is not None else _DEFAULT_MARKET_CATEGORY
        return await self._executor.run_with_redis_guard(
            "store_order_metadata",
            lambda: self._metadata_store.store(
                order_id,
                trade_rule=trade_rule,
                trade_reason=trade_reason,
                market_category=resolved,
                weather_station=weather_station,
            ),
        )

    async def get_order_metadata(self, order_id: str) -> Optional[Dict[str, str]]:
        return await self._executor.run_with_redis_guard("get_order_metadata", lambda: self._metadata_store.load(order_id))

    async def get_trades_by_date_range(self, start_date: date, end_date: date) -> List[Any]:
        return await self._executor.run_with_redis_guard(
            "get_trades_by_date_range",
            lambda: self._queries.trades_by_date_range(start_date, end_date),
        )

    async def get_trades_by_station(self, station: str) -> List[Any]:
        return await self._executor.run_with_redis_guard("get_trades_by_station", lambda: self._queries.trades_by_station(station))

    async def get_trades_by_rule(self, rule: str) -> List[Any]:
        return await self._executor.run_with_redis_guard("get_trades_by_rule", lambda: self._queries.trades_by_rule(rule))

    async def get_trades_closed_today(self) -> List[Any]:
        return await self._executor.run_with_redis_guard("get_trades_closed_today", self._queries.trades_closed_today)

    async def get_trades_closed_yesterday(self) -> List[Any]:
        return await self._executor.run_with_redis_guard("get_trades_closed_yesterday", self._queries.trades_closed_yesterday)

    async def get_unrealized_trades_for_date(self, target_date: date) -> List[Any]:
        return await self._executor.run_with_redis_guard(
            "get_unrealized_trades_for_date",
            lambda: self._queries.unrealized_trades_for_date(target_date),
        )

    async def store_daily_summary(self, summary: Any) -> bool:
        return await self._executor.run_with_redis_guard("store_daily_summary", lambda: self._pnl.store_daily_summary(summary))

    async def get_daily_summary(self, trade_date: date) -> Optional[Dict[str, Any]]:
        return await self._executor.run_with_redis_guard("get_daily_summary", lambda: self._pnl.get_daily_summary(trade_date))

    async def store_unrealized_pnl_data(self, redis_key: str, data: Dict[str, Any]) -> bool:
        return await self._executor.run_with_redis_guard(
            "store_unrealized_pnl_data",
            lambda: self._pnl.store_unrealized_snapshot(redis_key, data),
        )

    async def get_unrealized_pnl_data(self, redis_key: str) -> Optional[Dict[str, Any]]:
        return await self._executor.run_with_redis_guard("get_unrealized_pnl_data", lambda: self._pnl.get_unrealized_snapshot(redis_key))

    async def get_unrealized_pnl_history(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        return await self._executor.run_with_redis_guard(
            "get_unrealized_pnl_history",
            lambda: self._pnl.get_unrealized_history(start_date, end_date),
        )

    async def update_trade_prices(self, market_ticker: str, yes_bid: float, yes_ask: float) -> int:
        return await self._executor.run_with_redis_guard(
            "update_trade_prices",
            lambda: self._price_updater.update_market_prices(market_ticker, yes_bid=yes_bid, yes_ask=yes_ask),
        )


__all__ = ["TradeStore", "OrderMetadataError", "TradeStoreError", "TradeStoreShutdownError"]
