"""Factory for creating core KalshiStore components."""

from typing import TYPE_CHECKING, Optional

from redis.asyncio import Redis

from src.common.redis_protocol.kalshi_store.cleaner import KalshiMarketCleaner
from src.common.redis_protocol.kalshi_store.metadata import KalshiMetadataAdapter
from src.common.redis_protocol.kalshi_store.reader import KalshiMarketReader
from src.common.redis_protocol.kalshi_store.subscription import KalshiSubscriptionTracker
from src.common.redis_protocol.kalshi_store.writer import KalshiMarketWriter
from src.common.redis_protocol.weather_station_resolver import WeatherStationResolver

from ..connection import RedisConnectionManager

if TYPE_CHECKING:
    from logging import Logger


def create_core_components(
    redis: Optional[Redis],
    service_prefix: Optional[str],
    logger: "Logger",
    weather_resolver: "WeatherStationResolver",
):
    """Create core components for KalshiStore."""
    connection = RedisConnectionManager(logger=logger, redis=redis)
    metadata = KalshiMetadataAdapter(logger=logger, weather_resolver=weather_resolver)
    subscription = KalshiSubscriptionTracker(connection, logger, service_prefix)
    subscriptions_key = subscription.SUBSCRIPTIONS_KEY

    reader = KalshiMarketReader(
        connection,
        logger,
        metadata,
        service_prefix,
        subscriptions_key=subscriptions_key,
    )

    writer = KalshiMarketWriter(redis or connection.redis, logger, connection, metadata)

    cleaner = KalshiMarketCleaner(
        redis=redis,
        service_prefix=service_prefix,
        connection_manager=connection,
        subscriptions_key=subscriptions_key,
    )

    return connection, metadata, subscription, reader, writer, cleaner, subscriptions_key
