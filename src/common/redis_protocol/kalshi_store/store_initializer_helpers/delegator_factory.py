"""Factory for creating KalshiStore delegators."""

from dataclasses import dataclass

from common.redis_protocol.kalshi_store.attribute_resolver import (
    AttributeResolver,
    AttributeResolverDelegators,
)
from common.redis_protocol.kalshi_store.cleanup_delegator import CleanupDelegator
from common.redis_protocol.kalshi_store.facade_coordinator import (
    ConnectionDelegator,
    MarketQueryDelegator,
    MetadataDelegator,
    SubscriptionDelegator,
)
from common.redis_protocol.kalshi_store.facade_helpers_modules import PropertyManager
from common.redis_protocol.kalshi_store.orderbook_delegator import OrderbookDelegator
from common.redis_protocol.kalshi_store.utility_delegator import UtilityDelegator
from common.redis_protocol.kalshi_store.write_delegator import WriteDelegator


@dataclass(frozen=True)
class DelegatorSet:
    """Carrier for all KalshiStore delegator instances."""

    property_mgr: PropertyManager
    conn_delegator: ConnectionDelegator
    metadata_delegator: MetadataDelegator
    subscription_delegator: SubscriptionDelegator
    query_delegator: MarketQueryDelegator
    write_delegator: WriteDelegator
    orderbook_delegator: OrderbookDelegator
    cleanup_delegator: CleanupDelegator
    utility_delegator: UtilityDelegator


def create_delegators(
    connection,
    writer,
    reader,
    subscription,
    orderbook,
    cleaner,
    weather_resolver_getter,
):
    """Create all delegators and attribute resolver for KalshiStore."""
    property_mgr = PropertyManager(connection)
    conn_delegator = ConnectionDelegator(connection)
    metadata_delegator = MetadataDelegator(writer, reader, weather_resolver_getter)
    subscription_delegator = SubscriptionDelegator(subscription)
    query_delegator = MarketQueryDelegator(reader)
    write_delegator = WriteDelegator(writer, reader.get_market_key)
    orderbook_delegator = OrderbookDelegator(orderbook)
    cleanup_delegator = CleanupDelegator(cleaner)
    utility_delegator = UtilityDelegator(writer, reader, weather_resolver_getter())

    delegators = AttributeResolverDelegators(
        write_delegator=write_delegator,
        utility_delegator=utility_delegator,
        conn_delegator=conn_delegator,
        metadata_delegator=metadata_delegator,
        subscription_delegator=subscription_delegator,
        query_delegator=query_delegator,
        orderbook_delegator=orderbook_delegator,
        cleanup_delegator=cleanup_delegator,
    )

    attr_resolver = AttributeResolver(delegators)

    return (
        DelegatorSet(
            property_mgr=property_mgr,
            conn_delegator=conn_delegator,
            metadata_delegator=metadata_delegator,
            subscription_delegator=subscription_delegator,
            query_delegator=query_delegator,
            write_delegator=write_delegator,
            orderbook_delegator=orderbook_delegator,
            cleanup_delegator=cleanup_delegator,
            utility_delegator=utility_delegator,
        ),
        attr_resolver,
    )


from typing import TYPE_CHECKING, Optional

from redis.asyncio import Redis

from common.redis_protocol.kalshi_store.cleaner import KalshiMarketCleaner
from common.redis_protocol.kalshi_store.metadata import KalshiMetadataAdapter
from common.redis_protocol.kalshi_store.reader import KalshiMarketReader
from common.redis_protocol.kalshi_store.subscription import KalshiSubscriptionTracker
from common.redis_protocol.kalshi_store.writer import KalshiMarketWriter
from common.redis_protocol.weather_station_resolver import WeatherStationResolver

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
