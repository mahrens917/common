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

    async def update_interpolation_results(self, currency: str, mapping_results: Dict[str, Dict], get_market_key_func: Any) -> bool:
        return await _update_interpolation_results(self, currency, mapping_results, get_market_key_func)

    def _add_interpolation_fields_to_pipeline(self, pipe: Any, market_key: str, result: Dict[str, Any]) -> None:
        """Add interpolation result fields to pipeline."""
        from common.time_helpers.timezone import get_current_utc

        fields: Dict[str, str] = {
            "interpolation_method": str(result["interpolation_method"]),
            "deribit_points_used": str(int(result["deribit_points_used"])),
            "interpolation_quality_score": str(float(result["interpolation_quality_score"])),
            "interpolation_timestamp": get_current_utc().isoformat(),
        }

        t_bid = result.get("t_bid")
        t_ask = result.get("t_ask")
        if t_bid is not None:
            fields["t_bid"] = str(float(t_bid))
        if t_ask is not None:
            fields["t_ask"] = str(float(t_ask))
        if "interp_error_bid" in result:
            fields["interp_error_bid"] = str(float(result["interp_error_bid"]))
        if "interp_error_ask" in result:
            fields["interp_error_ask"] = str(float(result["interp_error_ask"]))

        pipe.hdel(market_key, "t_bids", "t_asks", "t_no_bids", "t_no_asks")
        pipe.hset(market_key, mapping=fields)


async def _check_markets_exist(redis: Any, market_keys: list, ticker_strings: list, currency: str) -> None:
    """Verify all markets exist in Redis, raising KalshiStoreError if any are missing."""
    try:
        exists_pipe = redis.pipeline()
        for market_key in market_keys:
            exists_pipe.exists(market_key)
        exists_results = await exists_pipe.execute()
    except REDIS_ERRORS as exc:
        raise KalshiStoreError(f"Redis error checking market existence for {currency} interpolation update") from exc
    for ticker_str, exists in zip(ticker_strings, exists_results):
        if not exists:
            raise KalshiStoreError(f"Kalshi market {ticker_str} missing in Redis during interpolation update")


async def _update_interpolation_results(self, currency: str, mapping_results: Dict[str, Dict], get_market_key_func: Any) -> bool:
    if not mapping_results:
        raise ValueError("mapping_results must not be empty")

    ticker_strings = [
        market_ticker.decode("utf-8") if isinstance(market_ticker, bytes) else str(market_ticker) for market_ticker in mapping_results
    ]
    market_keys = [get_market_key_func(ts) for ts in ticker_strings]

    await _check_markets_exist(self.redis, market_keys, ticker_strings, currency)

    pipe = self.redis.pipeline()
    updated_count = 0

    for (market_ticker, result), market_key, ticker_str in zip(mapping_results.items(), market_keys, ticker_strings):
        try:
            self._add_interpolation_fields_to_pipeline(pipe, market_key, result)
        except (TypeError, ValueError, KeyError) as exc:
            raise KalshiStoreError(f"Invalid interpolation payload for market {ticker_str}") from exc

        updated_count += 1

    try:
        await pipe.execute()
    except REDIS_ERRORS as exc:
        raise KalshiStoreError(f"Redis error executing interpolation updates for {currency}") from exc

    logger.info(
        "Successfully updated interpolation results for %s markets in %s",
        updated_count,
        currency,
    )
    return True
