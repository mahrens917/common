"""Helper functions for KalshiStoreDependenciesFactory."""

import logging
from typing import Callable, Optional

from redis.asyncio import Redis

from ..weather_station_resolver import WeatherStationResolver
from .attribute_resolver import AttributeResolver
from .cleaner import KalshiMarketCleaner
from .cleanup_delegator import CleanupDelegator
from .connection import RedisConnectionManager
from .facade_coordinator import (
    ConnectionDelegator,
    MarketQueryDelegator,
    MetadataDelegator,
    SubscriptionDelegator,
)
from .facade_helpers import PropertyManager
from .metadata import KalshiMetadataAdapter
from .orderbook import KalshiOrderbookProcessor
from .orderbook_delegator import OrderbookDelegator
from .reader import KalshiMarketReader
from .storage_delegator import StorageDelegator
from .subscription import KalshiSubscriptionTracker
from .utility_delegator import UtilityDelegator
from .write_delegator import WriteDelegator
from .writer import KalshiMarketWriter
from .writer_helpers.dependencies_factory import KalshiMarketWriterDependenciesFactory


def create_core_components(
    logger: logging.Logger,
    redis: Optional[Redis],
    service_prefix: Optional[str],
    weather_resolver: WeatherStationResolver,
    update_trade_prices_callback: Callable,
) -> dict:
    """Create core component instances."""
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

    writer_dependencies = KalshiMarketWriterDependenciesFactory.create(
        redis or connection.redis, logger, metadata, connection
    )
    writer = KalshiMarketWriter(
        redis or connection.redis,
        logger,
        connection,
        metadata,
        dependencies=writer_dependencies,
    )
    cleaner = KalshiMarketCleaner(
        redis=redis,
        service_prefix=service_prefix,
        connection_manager=connection,
        subscriptions_key=subscriptions_key,
    )
    orderbook = KalshiOrderbookProcessor(
        redis_connection_manager=connection,
        logger_instance=logger,
        update_trade_prices_callback=update_trade_prices_callback,
    )

    return {
        "connection": connection,
        "metadata": metadata,
        "reader": reader,
        "writer": writer,
        "subscription": subscription,
        "cleaner": cleaner,
        "orderbook": orderbook,
    }


def create_delegators(core: dict, weather_resolver: WeatherStationResolver) -> dict:
    """Create delegator instances."""
    property_mgr = PropertyManager(core["connection"])
    conn_delegator = ConnectionDelegator(core["connection"])
    metadata_delegator = MetadataDelegator(core["writer"], core["reader"], lambda: weather_resolver)
    subscription_delegator = SubscriptionDelegator(core["subscription"])
    query_delegator = MarketQueryDelegator(core["reader"])
    write_delegator = WriteDelegator(core["writer"], core["reader"].get_market_key)
    orderbook_delegator = OrderbookDelegator(core["orderbook"])
    cleanup_delegator = CleanupDelegator(core["cleaner"])
    utility_delegator = UtilityDelegator(core["writer"], core["reader"], weather_resolver)
    storage_delegator = StorageDelegator(core["writer"])

    return {
        "property_mgr": property_mgr,
        "conn_delegator": conn_delegator,
        "metadata_delegator": metadata_delegator,
        "subscription_delegator": subscription_delegator,
        "query_delegator": query_delegator,
        "write_delegator": write_delegator,
        "orderbook_delegator": orderbook_delegator,
        "cleanup_delegator": cleanup_delegator,
        "utility_delegator": utility_delegator,
        "storage_delegator": storage_delegator,
    }


def create_attribute_resolver(delegators: dict) -> AttributeResolver:
    """Create attribute resolver instance."""
    from .attribute_resolver import AttributeResolverDelegators

    config = AttributeResolverDelegators(
        storage_delegator=delegators["storage_delegator"],
        write_delegator=delegators["write_delegator"],
        utility_delegator=delegators["utility_delegator"],
        conn_delegator=delegators["conn_delegator"],
        metadata_delegator=delegators["metadata_delegator"],
        subscription_delegator=delegators["subscription_delegator"],
        query_delegator=delegators["query_delegator"],
        orderbook_delegator=delegators["orderbook_delegator"],
        cleanup_delegator=delegators["cleanup_delegator"],
    )
    return AttributeResolver(config)
