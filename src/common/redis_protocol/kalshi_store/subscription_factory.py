"""Dependency factory for KalshiSubscriptionTracker."""

import logging
from dataclasses import dataclass
from typing import Optional

from .connection import RedisConnectionManager
from .subscription_helpers import (
    ConnectionManager,
    KeyProvider,
    MarketSubscriptionManager,
    ServiceStatusManager,
    SubscriptionIdManager,
)


@dataclass
class KalshiSubscriptionTrackerDependencies:
    """Container for KalshiSubscriptionTracker dependencies."""

    connection_manager: ConnectionManager
    key_provider: KeyProvider
    market_subscription_manager: MarketSubscriptionManager
    subscription_id_manager: SubscriptionIdManager
    service_status_manager: ServiceStatusManager


class KalshiSubscriptionTrackerFactory:
    """Factory for creating KalshiSubscriptionTracker dependencies."""

    @staticmethod
    def create(
        redis_connection: RedisConnectionManager,
        logger_instance: logging.Logger,
        service_prefix: Optional[str],
    ) -> KalshiSubscriptionTrackerDependencies:
        """Create all dependencies for KalshiSubscriptionTracker."""
        connection_manager = ConnectionManager(redis_connection, logger_instance)
        key_provider = KeyProvider(service_prefix or "ws")
        market_subscription_manager = MarketSubscriptionManager(
            connection_manager.get_redis,
            key_provider.subscriptions_key,
            service_prefix or "ws",
        )
        subscription_id_manager = SubscriptionIdManager(
            connection_manager.get_redis,
            key_provider.subscription_ids_key,
            service_prefix or "ws",
        )
        service_status_manager = ServiceStatusManager(
            connection_manager.get_redis,
            key_provider.service_status_key,
        )

        return KalshiSubscriptionTrackerDependencies(
            connection_manager=connection_manager,
            key_provider=key_provider,
            market_subscription_manager=market_subscription_manager,
            subscription_id_manager=subscription_id_manager,
            service_status_manager=service_status_manager,
        )
