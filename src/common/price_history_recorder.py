"""
Price update recording for history tracking

Handles validation and persistence of BTC/ETH price updates to Redis hash structure
with automatic TTL management.
"""

import logging

from src.common.exceptions import ValidationError
from src.common.price_history_utils import generate_redis_key, validate_currency
from src.common.redis_protocol.config import HISTORY_TTL_SECONDS
from src.common.redis_protocol.typing import RedisClient, ensure_awaitable
from src.common.time_utils import get_current_utc

from .price_history_connection_manager import REDIS_ERRORS

logger = logging.getLogger(__name__)


class PriceHistoryRecorder:
    """
    Records price updates to Redis hash structure

    Validates currency and price inputs, generates timezone-aware timestamps,
    and persists to Redis with automatic TTL.
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

    async def record_price(
        self, client: RedisClient, currency: str, price: float
    ) -> tuple[bool, str]:
        """
        Record price update for BTC or ETH in Redis hash structure

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
        # Validate inputs - fail fast on invalid data
        validate_currency(currency)
        self.validate_price(price)

        try:
            # Generate timezone-aware datetime string as field name
            # Format: "2025-01-06 15:23:45+00:00" (ISO format with timezone)
            datetime_str = get_current_utc().isoformat()

            # Use simplified key format: history:btc or history:eth
            redis_key = generate_redis_key(currency)

            # Store in Redis hash with datetime as field and price as value
            await ensure_awaitable(client.hset(redis_key, datetime_str, str(float(price))))

            # Set TTL for automatic cleanup
            await ensure_awaitable(client.expire(redis_key, HISTORY_TTL_SECONDS))

            logger.debug(f"Recorded {currency} price history: ${price:.2f} at {datetime_str}")

        except REDIS_ERRORS as exc:
            logger.exception(f"Failed to record  price history: ")
            raise RuntimeError(f"Failed to record {currency} price history") from exc
        else:
            return True, datetime_str
