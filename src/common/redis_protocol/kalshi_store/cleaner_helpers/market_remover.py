"""
Market removal operations for KalshiMarketCleaner
"""

from __future__ import annotations

import logging

from ...error_types import REDIS_ERRORS
from .pipeline_executor import PipelineExecutor

logger = logging.getLogger(__name__)

_DEFAULT_KEY_PATTERNS = ("kalshi:*",)


def _resolve_key_patterns(patterns: list[str] | None) -> list[str]:
    if patterns:
        return patterns
    resolved: list[str] = []
    resolved.extend(_DEFAULT_KEY_PATTERNS)
    return resolved


def _decode_redis_key(value: object) -> str:
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8")
    return str(value)


class MarketRemover:
    """Handles complete market removal from Redis"""

    def __init__(
        self,
        redis_getter,
        subscriptions_key: str,
        subscribed_markets_key: str,
        service_prefix: str,
        get_market_key_callback,
        snapshot_key_callback=None,
    ):
        self._get_redis = redis_getter
        self.subscriptions_key = subscriptions_key
        self.subscribed_markets_key = subscribed_markets_key
        self.service_prefix = service_prefix
        self._get_market_key = get_market_key_callback
        self._get_snapshot_key = snapshot_key_callback

    async def remove_market_completely(self, market_ticker: str) -> bool:
        try:
            market_ticker_str = market_ticker.decode("utf-8") if isinstance(market_ticker, bytes) else str(market_ticker)
            market_key = self._get_market_key(market_ticker_str)
            snapshot_key = self._get_snapshot_key(market_ticker_str) if self._get_snapshot_key else None
            logger.debug(
                "Removing Kalshi market %s using key %s (service_prefix=%s)",
                market_ticker_str,
                market_key,
                self.service_prefix,
            )
            redis = await self._get_redis()
            pipe = redis.pipeline()
            pipe.srem(self.subscribed_markets_key, market_ticker_str)
            subscription_key = f"{self.service_prefix}:{market_ticker_str}"
            pipe.hdel(self.subscriptions_key, subscription_key)
            pipe.delete(market_key)
            if snapshot_key:
                pipe.delete(snapshot_key)
            success = await PipelineExecutor.execute_pipeline(pipe, f"remove market {market_ticker_str}")
            if success:
                logger.info(
                    "Successfully removed market %s completely from Redis",
                    market_ticker_str,
                )
                return True
            else:
                return success
        except REDIS_ERRORS as exc:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.error(
                "Error removing market %s completely from Redis: %s",
                market_ticker,
                exc,
                exc_info=True,
            )
            return False

    async def remove_all_kalshi_keys(self, *, patterns: list[str] | None = None) -> bool:
        try:
            redis = await self._get_redis()
            target_patterns = _resolve_key_patterns(patterns)
            keys_to_remove = set()
            for pattern in target_patterns:
                matched_keys = await redis.keys(pattern)
                keys_to_remove.update(_decode_redis_key(key) for key in matched_keys)

            if not keys_to_remove:
                logger.info("No Kalshi keys to remove for patterns: %s", target_patterns)
                return True
            logger.info(
                "Removing %s Kalshi keys from Redis using patterns %s",
                len(keys_to_remove),
                target_patterns,
            )
            pipe = redis.pipeline()
            for key in keys_to_remove:
                pipe.delete(key)
            success = await PipelineExecutor.execute_pipeline(pipe, "remove all Kalshi keys")
            if success:
                logger.info("Successfully removed all Kalshi keys for patterns %s", target_patterns)
                return True
            else:
                return False
        except REDIS_ERRORS as exc:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.error("Error removing all Kalshi keys: %s", exc, exc_info=True)
            return False
