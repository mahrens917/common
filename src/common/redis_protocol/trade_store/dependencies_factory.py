"""
Dependency factory for TradeStore.

This factory creates and wires all core dependencies needed by TradeStore,
reducing the number of direct instantiations in the main class.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from ..kalshi_store.connection import RedisConnectionManager
from ..typing import RedisClient
from .aggregations import TradeQueryService
from .codec import TradeRecordCodec
from .keys import TradeKeyBuilder
from .metadata import OrderMetadataStore
from .order_metadata_codec import OrderMetadataCodec
from .pnl import PnLStore
from .pricing import TradePriceUpdater
from .records import TradeRecordRepository
from .store_helpers import DependencyResolver, OperationExecutor, TradeStoreConnectionManager
from .store_helpers.api_delegator import TradeStoreAPIDelegator
from .store_helpers.pool_acquirer import PoolAcquirer


@dataclass
class TradeStoreDependencies:
    """Container for all TradeStore core dependencies."""

    base_connection: RedisConnectionManager
    connection_mgr: TradeStoreConnectionManager
    pool_acquirer: PoolAcquirer
    executor: OperationExecutor
    deps: DependencyResolver
    timezone: Any
    keys: TradeKeyBuilder
    codec: TradeRecordCodec
    metadata_codec: OrderMetadataCodec
    repository: TradeRecordRepository
    metadata_store: OrderMetadataStore
    queries: TradeQueryService
    pnl: PnLStore
    price_updater: TradePriceUpdater
    api: TradeStoreAPIDelegator


class TradeStoreDependenciesFactory:
    """Factory for creating TradeStore dependencies."""

    @staticmethod
    def create(
        logger: logging.Logger, redis: Optional[RedisClient], get_redis_func: Callable
    ) -> TradeStoreDependencies:
        """Create all core dependencies for TradeStore."""
        base_connection = RedisConnectionManager(logger=logger, redis=redis)
        connection_mgr = TradeStoreConnectionManager(logger, base_connection)
        pool_acquirer = PoolAcquirer(logger, connection_mgr)
        executor = OperationExecutor(logger)
        deps = DependencyResolver()
        timezone = deps.get_timezone_loader()()
        keys = TradeKeyBuilder()
        codec = TradeRecordCodec()
        metadata_codec = OrderMetadataCodec(timestamp_provider=deps.get_timestamp_provider())
        repository = TradeRecordRepository(
            get_redis_func, key_builder=keys, codec=codec, logger=logger
        )
        metadata_store = OrderMetadataStore(
            get_redis_func, key_builder=keys, codec=metadata_codec, logger=logger
        )
        queries = TradeQueryService(
            repository,
            key_builder=keys,
            logger=logger,
            timezone=timezone,
            start_date_loader=deps.get_start_date_loader(),
            timezone_aware_date_loader=deps.get_timezone_date_loader(),
        )
        pnl = PnLStore(get_redis_func, key_builder=keys, logger=logger)
        price_updater = TradePriceUpdater(
            repository,
            timezone=timezone,
            timezone_aware_date_loader=deps.get_timezone_date_loader(),
            current_time_provider=deps.get_timestamp_provider(),
            logger=logger,
        )
        api = TradeStoreAPIDelegator(
            repository, metadata_store, queries, pnl, price_updater, executor, deps
        )
        return TradeStoreDependencies(
            base_connection=base_connection,
            connection_mgr=connection_mgr,
            pool_acquirer=pool_acquirer,
            executor=executor,
            deps=deps,
            timezone=timezone,
            keys=keys,
            codec=codec,
            metadata_codec=metadata_codec,
            repository=repository,
            metadata_store=metadata_store,
            queries=queries,
            pnl=pnl,
            price_updater=price_updater,
            api=api,
        )
