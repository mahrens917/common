"""
Market Filter - Filter markets by various criteria

Handles market filtering logic based on status, expiry, and other attributes.
"""

import logging
from collections import Counter
from typing import List, Set

from redis.asyncio import Redis

from common.truthy import pick_truthy

from ....config.redis_schema import get_schema_config
from ....parsing_utils import decode_redis_key
from ....redis_schema import parse_kalshi_market_key

logger = logging.getLogger(__name__)
SCHEMA = get_schema_config()
_WEATHER_PREFIX = f"{SCHEMA.kalshi_weather_prefix}:"


class MarketFilter:
    """Filter markets by various criteria"""

    def __init__(self, logger_instance: logging.Logger):
        """
        Initialize market filter

        Args:
            logger_instance: Logger to use for filter operations
        """
        self.logger = logger_instance

    async def find_currency_market_tickers(self, redis: Redis, currency: str, is_market_for_currency_func) -> List[str]:
        """
        Scan Redis for Kalshi market tickers matching the requested currency.

        Args:
            redis: Redis connection
            currency: Currency to filter by
            is_market_for_currency_func: Function to check if ticker matches currency

        Returns:
            List of market tickers for the currency
        """
        pattern = f"{SCHEMA.kalshi_market_prefix}:*"
        cursor = 0
        collected: List[str] = []
        seen: Set[str] = set()

        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=500)
            for raw_key in keys:
                key_str = decode_redis_key(raw_key)
                if key_str.startswith(_WEATHER_PREFIX):
                    continue
                try:
                    descriptor = parse_kalshi_market_key(key_str)
                except ValueError as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
                    logger.warning("Failed to parse Kalshi market key: key=%r, error=%s", key_str, exc)
                    continue

                ticker = descriptor.ticker
                if ticker in seen:
                    continue
                if not is_market_for_currency_func(ticker, currency):
                    continue
                seen.add(ticker)
                collected.append(ticker)

            if cursor == 0:
                break

        return collected

    def log_market_summary(
        self,
        *,
        currency: str,
        total: int,
        processed: int,
        skip_reasons: Counter[str],
    ) -> None:
        """
        Log summary of market filtering results

        Args:
            currency: Currency being processed
            total: Total markets found
            processed: Markets successfully processed
            skip_reasons: Counter of skip reasons
        """
        if total <= 0:
            return
        skipped = total - processed
        expired = pick_truthy(skip_reasons.get("expired"), 0)
        self.logger.debug(
            "Processed %s/%s active markets for %s (expired=%s, skipped=%s)",
            processed,
            total,
            currency,
            expired,
            skipped,
        )
        if skip_reasons:
            top_reasons = ", ".join(f"{reason}={count}" for reason, count in skip_reasons.most_common(5))
            self.logger.debug("Top skip reasons for %s: %s", currency, top_reasons)
