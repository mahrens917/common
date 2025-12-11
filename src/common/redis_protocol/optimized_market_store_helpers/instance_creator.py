"""
Instance creation logic for OptimizedMarketStore
"""

import logging
from typing import TYPE_CHECKING, cast

from .redis_initializer import RedisInitializer

if TYPE_CHECKING:
    from ..optimized_market_store import OptimizedMarketStore

logger = logging.getLogger(__name__)


class InstanceCreator:
    """Handles creation of OptimizedMarketStore instances with Redis connections"""

    @staticmethod
    async def create_instance(cls_type: type) -> "OptimizedMarketStore":
        """
        Create a new OptimizedMarketStore instance with a Redis connection pool

        Args:
            cls_type: The OptimizedMarketStore class type

        Returns:
            OptimizedMarketStore instance
        """
        # Create Redis connection
        redis_client, redis_pool, initialized, atomic_ops = await RedisInitializer.create_with_pool()

        # Create instance without calling __init__
        instance = cast("OptimizedMarketStore", object.__new__(cls_type))

        # Set instance attributes
        instance.redis = redis_client
        instance.redis_pool = redis_pool
        instance.initialized = initialized
        instance.atomic_ops = atomic_ops
        instance.logger = logger

        # Import helper classes at runtime to avoid circular imports
        from .expiry_converter import ExpiryConverter
        from .instrument_fetcher import InstrumentFetcher
        from .market_data_fetcher import MarketDataFetcher
        from .spot_price_fetcher import SpotPriceFetcher

        # Initialize helper components
        redis_accessor = instance.get_redis_client
        instance.spot_price_fetcher = SpotPriceFetcher(redis_accessor, atomic_ops)
        instance.market_data_fetcher = MarketDataFetcher(redis_accessor)
        instance.instrument_fetcher = InstrumentFetcher(redis_accessor)
        instance.expiry_converter = ExpiryConverter()

        return instance
