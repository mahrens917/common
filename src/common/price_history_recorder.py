"""
Price update recording for history tracking

Handles validation and persistence of BTC/ETH price updates to Redis sorted set
with automatic TTL management and old-entry pruning.
"""

from __future__ import annotations

import logging

from common.exceptions import ValidationError
from common.price_history_utils import build_history_member, generate_redis_key, validate_currency
from common.redis_protocol.config import HISTORY_TTL_SECONDS
from common.redis_protocol.typing import RedisClient, ensure_awaitable
from common.time_utils import get_current_utc

from .price_history_connection_manager import REDIS_ERRORS

logger = logging.getLogger(__name__)


class PriceHistoryRecorder:
    """
    Records price updates to Redis sorted set

    Validates currency and price inputs, generates second-precision timestamps,
    and persists to Redis with automatic TTL and old-entry pruning.
    """

    @staticmethod
    def validate_price(price: float) -> None:
        """
        Validate price value

        Args:
            price: Price to validate

        Raises:
            ValueError: If price is not positive
        """
        if price <= 0:
            raise ValidationError(f"Invalid price: {price}. Must be positive.")

    async def record_price(self, client: RedisClient, currency: str, price: float) -> tuple[bool, str]:
        """
        Record price update for BTC or ETH in Redis sorted set

        Args:
            client: Redis client
            currency: Currency symbol ('BTC' or 'ETH')
            price: Price in USD

        Returns:
            Tuple of (success, datetime_str)

        Raises:
            ValueError: If currency is not 'BTC' or 'ETH'
            ValueError: If price is not positive
            RuntimeError: If Redis operation fails
        """
        validate_currency(currency)
        self.validate_price(price)

        try:
            current_time = get_current_utc()
            int_ts = int(current_time.timestamp())
            datetime_str = current_time.replace(microsecond=0).isoformat()

            redis_key = generate_redis_key(currency)
            score = float(int_ts)
            member = build_history_member(int_ts, float(price))
            cutoff = float(int_ts - HISTORY_TTL_SECONDS)

            pipe = client.pipeline()
            pipe.zremrangebyscore(redis_key, score, score)
            pipe.zadd(redis_key, {member: score})
            pipe.zremrangebyscore(redis_key, 0, cutoff)
            pipe.expire(redis_key, HISTORY_TTL_SECONDS)
            await ensure_awaitable(pipe.execute())

            logger.debug(f"Recorded {currency} price history: ${price:.2f} at {datetime_str}")

        except REDIS_ERRORS as exc:
            logger.exception(f"Failed to record {currency} price history")
            raise RuntimeError(f"Failed to record {currency} price history") from exc
        else:
            return True, datetime_str
