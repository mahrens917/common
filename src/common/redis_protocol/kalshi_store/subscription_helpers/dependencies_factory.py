from __future__ import annotations

"""Dependency factory for KalshiSubscriptionTracker."""


import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

_DEFAULT_SERVICE_PREFIX = "ws"

if TYPE_CHECKING:
    from ..connection import RedisConnectionManager
    from . import (
        ConnectionManager,
        KeyProvider,
        MarketSubscriptionManager,
        ServiceStatusManager,
        SubscriptionIdManager,
    )


@dataclass
class KalshiSubscriptionTrackerDependencies:
    """Container for all KalshiSubscriptionTracker dependencies."""  # gitleaks:allow

    connection_manager: "ConnectionManager"
    key_provider: "KeyProvider"
    market_subscription_manager: "MarketSubscriptionManager"
    subscription_id_manager: "SubscriptionIdManager"
    service_status_manager: "ServiceStatusManager"


class KalshiSubscriptionTrackerDependenciesFactory:  # gitleaks:allow
    """Factory for creating KalshiSubscriptionTracker dependencies."""

    @staticmethod
    def create(
        redis_connection: "RedisConnectionManager",
        logger_instance: logging.Logger,
        service_prefix: Optional[str],
    ) -> KalshiSubscriptionTrackerDependencies:  # gitleaks:allow
        """Create all dependencies for KalshiSubscriptionTracker."""
        from . import (
            ConnectionManager,
            KeyProvider,
            MarketSubscriptionManager,
            ServiceStatusManager,
            SubscriptionIdManager,
        )

        connection_manager = ConnectionManager(redis_connection, logger_instance)
        resolved_prefix = _DEFAULT_SERVICE_PREFIX if not service_prefix else service_prefix
        key_provider = KeyProvider(resolved_prefix)

        market_subscription_manager = MarketSubscriptionManager(
            connection_manager.get_redis,
            key_provider.subscriptions_key,
            resolved_prefix,
        )
        subscription_id_manager = SubscriptionIdManager(
            connection_manager.get_redis,
            key_provider.subscription_ids_key,
            resolved_prefix,
        )
        service_status_manager = ServiceStatusManager(
            connection_manager.get_redis,
            key_provider.service_status_key,
        )

        return KalshiSubscriptionTrackerDependencies(  # gitleaks:allow
            connection_manager=connection_manager,
            key_provider=key_provider,
            market_subscription_manager=market_subscription_manager,
            subscription_id_manager=subscription_id_manager,
            service_status_manager=service_status_manager,
        )
