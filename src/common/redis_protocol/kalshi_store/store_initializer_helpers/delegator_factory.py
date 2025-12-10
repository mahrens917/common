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
from common.redis_protocol.kalshi_store.facade_helpers_modules.property_manager import (
    PropertyManager,
)
from common.redis_protocol.kalshi_store.orderbook_delegator import OrderbookDelegator
from common.redis_protocol.kalshi_store.storage_delegator import StorageDelegator
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
    storage_delegator: StorageDelegator


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
    storage_delegator = StorageDelegator(writer)

    delegators = AttributeResolverDelegators(
        storage_delegator=storage_delegator,
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
            storage_delegator=storage_delegator,
        ),
        attr_resolver,
    )
