"""
Market update write operations.

This module handles writing enhanced market data and probability fields.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from redis.asyncio import Redis

from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable

if TYPE_CHECKING:
    from ..connection import RedisConnectionManager

logger = logging.getLogger(__name__)


class RedisConnectionMixin:
    _connection_manager: "RedisConnectionManager | None"
    redis: Optional[Redis]

    async def _ensure_redis(self) -> Redis:
        redis_client = self.redis
        if redis_client is None and self._connection_manager is not None:
            redis_client = await self._connection_manager.get_redis()
            self.redis = redis_client
        if redis_client is None:
            raise RuntimeError("Redis connection is not initialized for market update writes")
        return redis_client


class MarketDataMixin(RedisConnectionMixin):
    _format_probability: Any

    async def write_enhanced_market_data(
        self, market_ticker: str, market_key: str, field_updates: Dict[str, Any]
    ) -> bool:
        return await self._write_enhanced_market_data(market_ticker, market_key, field_updates)

    async def _write_enhanced_market_data(
        self, market_ticker: str, market_key: str, field_updates: Dict[str, Any]
    ) -> bool:
        if not market_ticker:
            raise TypeError("market_ticker must be provided for write_enhanced_market_data")

        if not field_updates:
            raise ValueError("field_updates must contain at least one field to persist")

        redis_client = await self._ensure_redis()
        pipe = redis_client.pipeline(transaction=True)

        try:
            for field_name, value in field_updates.items():
                pipe.hset(market_key, field_name, self._format_probability(value))

            await ensure_awaitable(pipe.execute())
            logger.debug(
                "Persisted enhanced data for %s with fields: %s",
                market_ticker,
                sorted(field_updates.keys()),
            )
        except REDIS_ERRORS as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to persist enhanced data for %s: %s", market_ticker, exc, exc_info=True
            )
            raise
        else:
            return True


class TradePriceMixin:
    _trade_store_lock: asyncio.Lock
    _trade_store: Any

    async def update_trade_prices_for_market(
        self, market_ticker: str, yes_bid: Optional[float], yes_ask: Optional[float]
    ) -> None:
        await self._update_trade_prices(market_ticker, yes_bid, yes_ask)

    async def _update_trade_prices(
        self, market_ticker: str, yes_bid: Optional[float], yes_ask: Optional[float]
    ) -> None:
        if yes_bid is None or yes_ask is None:
            return
        try:
            from ...trade_store import TradeStoreError

            trade_store = await self._get_trade_store()
            await ensure_awaitable(trade_store.update_trade_prices(market_ticker, yes_bid, yes_ask))
        except REDIS_ERRORS as exc:
            logger.error(
                "Redis error updating trade prices for market %s: %s",
                market_ticker,
                exc,
                exc_info=True,
            )
        except TradeStoreError as exc:
            logger.error(
                "TradeStore error updating prices for market %s: %s",
                market_ticker,
                exc,
                exc_info=True,
            )
        except (ValueError, TypeError) as exc:
            logger.error(
                "Invalid trade price payload for market %s: %s",
                market_ticker,
                exc,
                exc_info=True,
            )

    async def _get_trade_store(self):
        if self._trade_store is not None:
            return self._trade_store

        async with self._trade_store_lock:
            if self._trade_store is not None:
                return self._trade_store

            from ...trade_store import TradeStore, TradeStoreError

            trade_store = TradeStore()
            initialize_method = getattr(trade_store, "initialize", None)
            if callable(initialize_method):
                initialized = initialize_method()
                if asyncio.iscoroutine(initialized):
                    initialized = await initialized
                if initialized is False:
                    raise TradeStoreError("Failed to initialize TradeStore for price updates")
            self._trade_store = trade_store
            return trade_store


class MarketUpdateWriter(MarketDataMixin, TradePriceMixin):
    """Handles market update write operations."""

    def __init__(
        self,
        redis_connection: Optional[Redis],
        logger_instance: logging.Logger,
        format_probability_func: Any,
        connection_manager: Optional["RedisConnectionManager"] = None,
    ):
        self.redis = redis_connection
        self.logger = logger_instance
        self._format_probability = format_probability_func
        self._connection_manager = connection_manager
        self._trade_store: Optional[Any] = None
        self._trade_store_lock = asyncio.Lock()
