from __future__ import annotations

"""Dependency factory for KalshiMarketWriter."""


import logging
from dataclasses import dataclass

from redis.asyncio import Redis

from ..connection import RedisConnectionManager
from ..metadata import KalshiMetadataAdapter
from . import (
    BatchReader,
    BatchWriter,
    MarketUpdateWriter,
    MetadataWriter,
    OrderbookWriter,
    SubscriptionWriter,
    ValidationWriter,
)


@dataclass
class KalshiMarketWriterDependencies:
    """Container for all KalshiMarketWriter helper dependencies."""

    validation: ValidationWriter
    metadata_writer: MetadataWriter
    market_updater: MarketUpdateWriter
    orderbook: OrderbookWriter
    batch: BatchWriter
    batch_reader: BatchReader
    subscription: SubscriptionWriter


class KalshiMarketWriterDependenciesFactory:
    """Factory for creating KalshiMarketWriter helper dependencies."""

    @staticmethod
    def create(
        redis_connection: Redis,
        logger_instance: logging.Logger,
        metadata_adapter: KalshiMetadataAdapter,
        connection_manager: RedisConnectionManager,
    ) -> KalshiMarketWriterDependencies:
        """
        Create all helper dependencies for KalshiMarketWriter.

        Args:
            redis_connection: Active Redis connection
            logger_instance: Logger instance
            metadata_adapter: Metadata adapter for market data processing

        Returns:
            KalshiMarketWriterDependencies container with all helpers
        """
        # Create helper instances
        validation = ValidationWriter(redis_connection, logger_instance)
        metadata_writer = MetadataWriter(redis_connection, logger_instance, metadata_adapter, connection_manager)
        market_updater = MarketUpdateWriter(
            redis_connection,
            logger_instance,
            ValidationWriter.format_probability_value,
            connection_manager,
        )
        orderbook = OrderbookWriter(redis_connection, logger_instance)
        batch = BatchWriter(redis_connection, logger_instance)
        batch_reader = BatchReader(redis_connection, logger_instance)
        subscription = SubscriptionWriter(redis_connection, logger_instance, metadata_adapter)

        return KalshiMarketWriterDependencies(
            validation=validation,
            metadata_writer=metadata_writer,
            market_updater=market_updater,
            orderbook=orderbook,
            batch=batch,
            batch_reader=batch_reader,
            subscription=subscription,
        )
