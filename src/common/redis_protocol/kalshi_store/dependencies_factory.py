"""
Dependency factory for KalshiStore.

This factory creates and wires all core dependencies needed by KalshiStore,
reducing the number of direct instantiations in the main class.
"""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from redis.asyncio import Redis

from ..weather_station_resolver import WeatherStationResolver
from . import dependencies_factory_helpers as factory_helpers
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


@dataclass
class KalshiStoreDependencies:
    """Container for all KalshiStore core dependencies."""

    connection: RedisConnectionManager
    metadata: KalshiMetadataAdapter
    reader: KalshiMarketReader
    writer: KalshiMarketWriter
    subscription: KalshiSubscriptionTracker
    cleaner: KalshiMarketCleaner
    orderbook: KalshiOrderbookProcessor
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
    attr_resolver: AttributeResolver


class KalshiStoreDependenciesFactory:
    """Factory for creating KalshiStore dependencies."""

    @staticmethod
    def create(
        logger: logging.Logger,
        redis: Optional[Redis],
        service_prefix: Optional[str],
        weather_resolver: WeatherStationResolver,
        update_trade_prices_callback: Callable,
    ) -> KalshiStoreDependencies:
        """
        Create all core dependencies for KalshiStore.

        Args:
            logger: Logger instance
            redis: Optional Redis client
            service_prefix: Service prefix ('rest' or 'ws')
            weather_resolver: Weather station resolver instance
            update_trade_prices_callback: Callback for trade price updates

        Returns:
            KalshiStoreDependencies container with all components wired together
        """
        # Create core components
        core = factory_helpers.create_core_components(
            logger, redis, service_prefix, weather_resolver, update_trade_prices_callback
        )

        # Create delegators
        delegators = factory_helpers.create_delegators(core, weather_resolver)

        # Create attribute resolver
        attr_resolver = factory_helpers.create_attribute_resolver(delegators)

        return KalshiStoreDependencies(
            connection=core["connection"],
            metadata=core["metadata"],
            reader=core["reader"],
            writer=core["writer"],
            subscription=core["subscription"],
            cleaner=core["cleaner"],
            orderbook=core["orderbook"],
            property_mgr=delegators["property_mgr"],
            conn_delegator=delegators["conn_delegator"],
            metadata_delegator=delegators["metadata_delegator"],
            subscription_delegator=delegators["subscription_delegator"],
            query_delegator=delegators["query_delegator"],
            write_delegator=delegators["write_delegator"],
            orderbook_delegator=delegators["orderbook_delegator"],
            cleanup_delegator=delegators["cleanup_delegator"],
            utility_delegator=delegators["utility_delegator"],
            storage_delegator=delegators["storage_delegator"],
            attr_resolver=attr_resolver,
        )
