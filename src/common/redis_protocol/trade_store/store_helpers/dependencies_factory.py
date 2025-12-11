from __future__ import annotations

"""Dependency factory for TradeStore."""


import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ...kalshi_store.connection import RedisConnectionManager
    from ..aggregations import TradeQueryService
    from ..codec import TradeRecordCodec
    from ..keys import TradeKeyBuilder
    from ..metadata import OrderMetadataStore
    from ..pnl import PnLStore
    from ..pricing import TradePriceUpdater
    from ..records import TradeRecordRepository
    from . import DependencyResolver, OperationExecutor, TradeStoreConnectionManager
    from .pool_acquirer import PoolAcquirer


@dataclass
class TradeStoreDependencies:
    """Container for all TradeStore dependencies."""

    connection_mgr: "TradeStoreConnectionManager"
    pool_acquirer: "PoolAcquirer"
    executor: "OperationExecutor"
    deps: "DependencyResolver"
    keys: "TradeKeyBuilder"
    codec: "TradeRecordCodec"
    repository: "TradeRecordRepository"
    metadata_store: "OrderMetadataStore"
    queries: "TradeQueryService"
    pnl: "PnLStore"
    price_updater: "TradePriceUpdater"


class TradeStoreDependenciesFactory:
    """Factory for creating TradeStore dependencies."""

    @staticmethod
    def create(
        logger: logging.Logger,
        base_connection: "RedisConnectionManager",
        get_redis: Callable,
        timezone,
    ) -> TradeStoreDependencies:
        """Create all dependencies for TradeStore."""
        from ..aggregations import TradeQueryService
        from ..codec import OrderMetadataCodec, TradeRecordCodec
        from ..keys import TradeKeyBuilder
        from ..metadata import OrderMetadataStore
        from ..pnl import PnLStore
        from ..pricing import TradePriceUpdater
        from ..records import TradeRecordRepository
        from . import DependencyResolver, OperationExecutor, TradeStoreConnectionManager
        from .pool_acquirer import PoolAcquirer

        connection_mgr = TradeStoreConnectionManager(logger, base_connection)
        pool_acquirer = PoolAcquirer(logger, connection_mgr)
        executor = OperationExecutor(logger)
        deps = DependencyResolver()

        # Initialize keys and codecs
        keys = TradeKeyBuilder()
        codec = TradeRecordCodec()
        metadata_codec = OrderMetadataCodec(timestamp_provider=deps.get_timestamp_provider())

        # Initialize repositories and services
        repository = TradeRecordRepository(get_redis, key_builder=keys, codec=codec, logger=logger)
        metadata_store = OrderMetadataStore(get_redis, key_builder=keys, codec=metadata_codec, logger=logger)
        queries = TradeQueryService(
            repository,
            key_builder=keys,
            logger=logger,
            timezone=timezone,
            start_date_loader=deps.get_start_date_loader(),
            timezone_aware_date_loader=deps.get_timezone_date_loader(),
        )
        pnl = PnLStore(get_redis, key_builder=keys, logger=logger)
        price_updater = TradePriceUpdater(
            repository,
            timezone=timezone,
            timezone_aware_date_loader=deps.get_timezone_date_loader(),
            current_time_provider=deps.get_timestamp_provider(),
            logger=logger,
        )

        return TradeStoreDependencies(
            connection_mgr=connection_mgr,
            pool_acquirer=pool_acquirer,
            executor=executor,
            deps=deps,
            keys=keys,
            codec=codec,
            repository=repository,
            metadata_store=metadata_store,
            queries=queries,
            pnl=pnl,
            price_updater=price_updater,
        )
