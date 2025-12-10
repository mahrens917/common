"""
Batch read operations for interpolation results.

This module handles reading interpolation results from Redis.
"""

import logging
from typing import Any, Dict, List

from redis.asyncio import Redis

from ....redis_schema import parse_kalshi_market_key
from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable

logger = logging.getLogger(__name__)


class BatchReader:
    """Handles batch read operations for interpolation results."""

    def __init__(self, redis_connection: Redis, logger_instance: logging.Logger):
        self.redis = redis_connection
        self.logger = logger_instance

    async def get_interpolation_results(
        self,
        currency: str,
        market_keys: List[str],
        string_or_default_func: Any,
        int_or_default_func: Any,
        float_or_default_func: Any,
    ) -> Dict[str, Dict]:
        try:
            if not market_keys:
                logger.warning("No Kalshi markets found in Redis")
                return {}

            logger.info(
                "Found %s Kalshi markets, checking for interpolation data", len(market_keys)
            )

            import sys

            results = {}
            module = sys.modules.get("common.redis_protocol.kalshi_store")
            key_parser = getattr(module, "parse_kalshi_market_key", parse_kalshi_market_key)

            for key in market_keys:
                result = await self._extract_single_interpolation_result(
                    key,
                    currency,
                    key_parser,
                    string_or_default_func,
                    int_or_default_func,
                    float_or_default_func,
                )
                if result:
                    results[result[0]] = result[1]

            else:
                return results
        except REDIS_ERRORS as exc:
            logger.error(
                "Redis error getting interpolation results for %s: %s", currency, exc, exc_info=True
            )
            return {}

    async def _extract_single_interpolation_result(
        self, key_str: str, curr: str, parser: Any, str_f: Any, int_f: Any, float_f: Any
    ) -> Any:
        try:
            desc = parser(key_str)
        except ValueError:
            return None

        ticker = desc.ticker
        data = await ensure_awaitable(self.redis.hgetall(key_str))
        if not data or curr.upper() not in ticker.upper():
            return None

        yes_bid = data.get("t_yes_bid")
        yes_ask = data.get("t_yes_ask")
        if yes_bid is None and yes_ask is None:
            return None

        try:
            return (
                ticker,
                {
                    "t_yes_bid": float(yes_bid) if yes_bid is not None else None,
                    "t_yes_ask": float(yes_ask) if yes_ask is not None else None,
                    "interpolation_method": str_f(data.get("interpolation_method")),
                    "deribit_points_used": int_f(data.get("deribit_points_used"), None),
                    "interpolation_quality_score": float_f(
                        data.get("interpolation_quality_score"), 0.0
                    ),
                    "interpolation_timestamp": str_f(data.get("interpolation_timestamp")),
                    "interp_error_bid": float_f(data.get("interp_error_bid"), 0.0),
                    "interp_error_ask": float_f(data.get("interp_error_ask"), 0.0),
                },
            )
        except (ValueError, KeyError):
            self.logger.warning("Error parsing interpolation results for %s", ticker)
