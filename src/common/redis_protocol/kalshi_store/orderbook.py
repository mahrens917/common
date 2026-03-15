import logging
import time
from typing import TYPE_CHECKING, Any, Dict

from redis.asyncio import Redis

from ...redis_schema import KalshiMarketDescriptor, describe_kalshi_ticker
from ..error_types import REDIS_ERRORS
from .connection import RedisConnectionManager
from .orderbook_helpers import DeltaProcessor, SnapshotProcessor
from .orderbook_helpers.message_processing import normalizer
from .orderbook_helpers.message_processing.normalizer import OrderbookMessageContext

if TYPE_CHECKING:
    from .orderbook_helpers.orderbook_cache import OrderbookCache

logger = logging.getLogger(__name__)


class KalshiOrderbookProcessor:
    def __init__(
        self,
        redis_connection_manager: RedisConnectionManager,
        logger_instance: logging.Logger,
        update_trade_prices_callback: Any,
    ):
        self._connection_manager = redis_connection_manager
        self._logger = logger_instance
        self._update_trade_prices_callback = update_trade_prices_callback
        self._cache: "OrderbookCache | None" = None
        self._snapshot_processor = SnapshotProcessor(update_trade_prices_callback)
        self._delta_processor = DeltaProcessor(update_trade_prices_callback)
        self._market_key_cache: Dict[str, str] = {}

    def set_cache(self, cache: "OrderbookCache") -> None:
        """Attach cache to both processors for in-memory orderbook tracking."""
        self._cache = cache
        self._snapshot_processor.set_cache(cache)
        self._delta_processor.set_cache(cache)

    def evict_market(self, market_key: str) -> None:
        """Remove a market from the in-memory cache after unsubscribe."""
        if self._cache is not None:
            self._cache.remove_market(market_key)

    async def _get_redis(self) -> Redis:
        return await self._connection_manager.get_redis()

    async def _ensure_redis_connection(self) -> bool:
        try:
            await self._get_redis()
        except RuntimeError:  # Expected runtime failure in operation  # policy_guard: allow-silent-handler
            logger.warning("Expected runtime failure in operation")
            return False
        else:
            return True

    def get_market_key(self, market_ticker: str) -> str:
        cached = self._market_key_cache.get(market_ticker)
        if cached is not None:
            return cached
        key = describe_kalshi_ticker(market_ticker).key
        self._market_key_cache[market_ticker] = key
        return key

    def _market_descriptor(self, market_ticker: str) -> KalshiMarketDescriptor:
        return describe_kalshi_ticker(market_ticker)

    async def process_snapshot(
        self, *, redis: Redis, market_key: str, market_ticker: str, msg_data: Dict[str, Any], timestamp: str
    ) -> bool:
        return await self._snapshot_processor.process_orderbook_snapshot(
            redis=redis,
            market_key=market_key,
            market_ticker=market_ticker,
            msg_data=msg_data,
            timestamp=timestamp,
        )

    async def process_delta(self, *, redis: Redis, market_key: str, market_ticker: str, msg_data: Dict[str, Any], timestamp: str) -> bool:
        return await self._delta_processor.process_orderbook_delta(
            redis=redis,
            market_key=market_key,
            market_ticker=market_ticker,
            msg_data=msg_data,
            timestamp=timestamp,
        )

    async def process_orderbook_pre_parsed(self, *, msg_type: str, msg_data: Dict[str, Any], market_ticker: str, timestamp: str) -> bool:
        """Process an orderbook message with already-extracted fields.

        Skips payload re-merging, ticker re-parsing, and per-message connection
        checks — use from the WebSocket hot path where these are redundant.
        """
        market_key = self.get_market_key(market_ticker)
        redis = await self._get_redis()
        context = OrderbookMessageContext(
            msg_type=msg_type,
            msg_data=msg_data,
            market_ticker=market_ticker,
            market_key=market_key,
            timestamp=timestamp,
            redis=redis,
            snapshot_processor=self._snapshot_processor,
            delta_processor=self._delta_processor,
        )
        return await normalizer.process_orderbook_message(context)

    async def update_orderbook(
        self,
        message: Dict,
        *,
        pre_parsed_type: str | None = None,
        pre_parsed_data: Dict[str, Any] | None = None,
        pre_parsed_ticker: str | None = None,
        pre_parsed_timestamp: str | None = None,
    ) -> bool:
        if pre_parsed_type is not None and pre_parsed_data is not None and pre_parsed_ticker is not None:
            timestamp = pre_parsed_timestamp if pre_parsed_timestamp is not None else str(int(time.time()))
            return await self.process_orderbook_pre_parsed(
                msg_type=pre_parsed_type, msg_data=pre_parsed_data, market_ticker=pre_parsed_ticker, timestamp=timestamp
            )
        return await self._update_orderbook_from_message(message)

    async def _update_orderbook_from_message(self, message: Dict) -> bool:
        """Parse and process a raw orderbook message (slow path for REST snapshots)."""
        try:
            if not await self._ensure_redis_connection():
                logger.error("Failed to ensure Redis connection for update_orderbook")
                return False
            from . import merge_orderbook_payload

            msg_type, msg_data, market_ticker = merge_orderbook_payload(message)
            return await self.process_orderbook_pre_parsed(
                msg_type=msg_type, msg_data=msg_data, market_ticker=market_ticker, timestamp=str(int(time.time()))
            )
        except (
            ValueError,
            KeyError,
            RuntimeError,
        ) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            error_msg = str(exc)
            if "Missing yes_bid_price" in error_msg or "Missing yes_ask_price" in error_msg:
                logger.debug("Illiquid market orderbook update: %s", exc)
                return True
            logger.error("Invalid orderbook update payload: %s", exc, exc_info=True)
            return False
        except REDIS_ERRORS as exc:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.error("Redis error updating orderbook: %s", exc, exc_info=True)
            return False
