import logging
import time
from typing import Any, Dict

from redis.asyncio import Redis

from ...redis_schema import KalshiMarketDescriptor, describe_kalshi_ticker
from ..error_types import REDIS_ERRORS
from .connection import RedisConnectionManager
from .orderbook_helpers import DeltaProcessor, SnapshotProcessor
from .orderbook_helpers.message_processing import dispatcher, normalizer
from .orderbook_helpers.message_processing.dispatcher import OrderbookMessageContext

logger = logging.getLogger(__name__)


async def _process_orderbook_message(*, context: OrderbookMessageContext) -> bool:
    return await dispatcher.process_orderbook_message(context)


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
        self._snapshot_processor = SnapshotProcessor(update_trade_prices_callback)
        self._delta_processor = DeltaProcessor(update_trade_prices_callback)

    async def _get_redis(self) -> Redis:
        return await self._connection_manager.get_redis()

    async def _ensure_redis_connection(self) -> bool:
        try:
            await self._get_redis()
        except RuntimeError:  # policy_guard: allow-silent-handler
            return False
        else:
            return True

    def get_market_key(self, market_ticker: str) -> str:
        return describe_kalshi_ticker(market_ticker).key

    def _market_descriptor(self, market_ticker: str) -> KalshiMarketDescriptor:
        return describe_kalshi_ticker(market_ticker)

    async def process_snapshot(
        self,
        *,
        redis: Redis,
        market_key: str,
        market_ticker: str,
        msg_data: Dict[str, Any],
        timestamp: str,
    ) -> bool:
        return await self._snapshot_processor.process_orderbook_snapshot(
            redis=redis,
            market_key=market_key,
            market_ticker=market_ticker,
            msg_data=msg_data,
            timestamp=timestamp,
        )

    async def process_delta(
        self,
        *,
        redis: Redis,
        market_key: str,
        market_ticker: str,
        msg_data: Dict[str, Any],
        timestamp: str,
    ) -> bool:
        return await self._delta_processor.process_orderbook_delta(
            redis=redis,
            market_key=market_key,
            market_ticker=market_ticker,
            msg_data=msg_data,
            timestamp=timestamp,
        )

    async def update_orderbook(self, message: Dict) -> bool:
        try:
            if not await self._ensure_redis_connection():
                logger.error("Failed to ensure Redis connection for update_orderbook")
                return False
            from . import merge_orderbook_payload

            msg_type, msg_data, market_ticker = merge_orderbook_payload(message)
            market_key = self.get_market_key(market_ticker)
            timestamp = str(int(time.time()))
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
            success = await _process_orderbook_message(context=context)
            if success and msg_type == "orderbook_snapshot":
                await normalizer.normalize_snapshot_json(redis, market_key)
        except (ValueError, KeyError, RuntimeError) as exc:  # policy_guard: allow-silent-handler
            error_msg = str(exc)
            if "Missing yes_bid_price" in error_msg or "Missing yes_ask_price" in error_msg:
                logger.debug("Illiquid market orderbook update: %s", exc)
                return True
            logger.error("Invalid orderbook update payload: %s", exc, exc_info=True)
            return False
        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.error("Redis error updating orderbook: %s", exc, exc_info=True)
            return False
        else:
            return success
