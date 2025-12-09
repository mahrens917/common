"""
Batch write operations for interpolation results.

This module handles batch updates of interpolation results to Redis.
"""

import logging
from typing import Any, Dict

from redis.asyncio import Redis

from ...error_types import REDIS_ERRORS

logger = logging.getLogger(__name__)


class KalshiStoreError(RuntimeError):
    """Raised when KalshiStore operations cannot complete successfully."""


class BatchWriter:
    """Handles batch write operations for interpolation results."""

    def __init__(self, redis_connection: Redis, logger_instance: logging.Logger):
        """
        Initialize BatchWriter.

        Args:
            redis_connection: Active Redis connection
            logger_instance: Logger instance
        """
        self.redis = redis_connection
        self.logger = logger_instance

    async def update_interpolation_results(
        self, currency: str, mapping_results: Dict[str, Dict], get_market_key_func: Any
    ) -> bool:
        return await _update_interpolation_results(
            self, currency, mapping_results, get_market_key_func
        )

    def _add_interpolation_fields_to_pipeline(
        self, pipe: Any, market_key: str, result: Dict[str, Any]
    ) -> None:
        """Add interpolation result fields to pipeline."""
        t_yes_bid = result.get("t_yes_bid")
        t_yes_ask = result.get("t_yes_ask")

        if t_yes_bid is not None:
            pipe.hset(market_key, "t_yes_bid", str(float(t_yes_bid)))
        if t_yes_ask is not None:
            pipe.hset(market_key, "t_yes_ask", str(float(t_yes_ask)))

        pipe.hdel(market_key, "t_yes_bids", "t_yes_asks", "t_no_bids", "t_no_asks")
        pipe.hset(market_key, "interpolation_method", str(result["interpolation_method"]))
        pipe.hset(market_key, "deribit_points_used", str(int(result["deribit_points_used"])))
        pipe.hset(
            market_key,
            "interpolation_quality_score",
            str(float(result["interpolation_quality_score"])),
        )

        if "interp_error_bid" in result:
            pipe.hset(market_key, "interp_error_bid", str(float(result["interp_error_bid"])))
        if "interp_error_ask" in result:
            pipe.hset(market_key, "interp_error_ask", str(float(result["interp_error_ask"])))

        from src.common.time_helpers.timezone import get_current_utc

        pipe.hset(market_key, "interpolation_timestamp", get_current_utc().isoformat())


async def _update_interpolation_results(
    self, currency: str, mapping_results: Dict[str, Dict], get_market_key_func: Any
) -> bool:
    if not mapping_results:
        raise ValueError("mapping_results must not be empty")

    pipe = self.redis.pipeline()
    updated_count = 0

    for market_ticker, result in mapping_results.items():
        market_ticker_str = (
            market_ticker.decode("utf-8")
            if isinstance(market_ticker, bytes)
            else str(market_ticker)
        )

        market_key = get_market_key_func(market_ticker_str)
        try:
            market_data = await self.redis.hgetall(market_key)
        except REDIS_ERRORS as exc:
            raise KalshiStoreError(
                f"Redis error loading market {market_ticker_str} for interpolation update"
            ) from exc

        if not market_data:
            raise KalshiStoreError(
                f"Kalshi market {market_ticker_str} missing in Redis during interpolation update"
            )

        try:
            self._add_interpolation_fields_to_pipeline(pipe, market_key, result)
        except (TypeError, ValueError, KeyError) as exc:
            raise KalshiStoreError(
                f"Invalid interpolation payload for market {market_ticker_str}"
            ) from exc

        updated_count += 1

    try:
        await pipe.execute()
    except REDIS_ERRORS as exc:
        raise KalshiStoreError(
            f"Redis error executing interpolation updates for {currency}"
        ) from exc

    logger.info(
        "Successfully updated interpolation results for %s markets in %s",
        updated_count,
        currency,
    )
    return True
