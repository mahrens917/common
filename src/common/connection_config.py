"""
Configuration module for connection management across all services.

This module provides centralized configuration for connection timeouts, retry intervals,
and backoff parameters. All values are derived from production requirements and
operational experience to eliminate magic numbers throughout the codebase.

Configuration is loaded from JSON config files with environment variable overrides.
"""

from dataclasses import dataclass, field
from functools import partial

from common.connectionconfig_helpers.config_loader import (
    require_env_float,
    require_env_int,
)
from common.connectionconfig_helpers.service_config_builder import (
    get_service_specific_config,
)


@dataclass
class ConnectionConfig:
    """
    Centralized configuration for connection management.

    All timeout and interval values are in seconds and derived from production
    operational requirements. These values eliminate magic numbers and provide
    consistent behavior across all services.

    Attributes:
        connection_timeout_seconds: Maximum time to wait for initial connection
        request_timeout_seconds: Maximum time to wait for individual requests
        reconnection_initial_delay_seconds: Initial delay before first reconnection attempt
        reconnection_max_delay_seconds: Maximum delay between reconnection attempts
        reconnection_backoff_multiplier: Multiplier for exponential backoff
        max_consecutive_failures: Maximum failures before extended backoff
        health_check_interval_seconds: Interval between connection health checks
        subscription_timeout_seconds: Maximum time to wait for subscription confirmation
    """

    # Connection establishment timeouts
    connection_timeout_seconds: int = field(
        default_factory=partial(require_env_int, "CONNECTION_TIMEOUT_SECONDS")
    )
    request_timeout_seconds: int = field(
        default_factory=partial(require_env_int, "REQUEST_TIMEOUT_SECONDS")
    )

    # Reconnection backoff configuration
    reconnection_initial_delay_seconds: int = field(
        default_factory=partial(require_env_int, "RECONNECTION_INITIAL_DELAY_SECONDS")
    )
    reconnection_max_delay_seconds: int = field(
        default_factory=partial(require_env_int, "RECONNECTION_MAX_DELAY_SECONDS")
    )
    reconnection_backoff_multiplier: float = field(
        default_factory=partial(require_env_float, "RECONNECTION_BACKOFF_MULTIPLIER")
    )
    max_consecutive_failures: int = field(
        default_factory=partial(require_env_int, "MAX_CONSECUTIVE_FAILURES")
    )

    # Health monitoring configuration
    health_check_interval_seconds: int = field(
        default_factory=partial(require_env_int, "HEALTH_CHECK_INTERVAL_SECONDS")
    )

    # WebSocket subscription configuration
    subscription_timeout_seconds: int = field(
        default_factory=partial(require_env_int, "SUBSCRIPTION_TIMEOUT_SECONDS")
    )


def get_connection_config(service_name: str | None = None) -> ConnectionConfig:
    """
    Factory function to get connection configuration for a specific service.

    Args:
        service_name: Optional service name for service-specific overrides

    Returns:
        ConnectionConfig instance with appropriate settings
    """
    base_config = ConnectionConfig()

    if service_name:
        # Apply service-specific overrides
        overrides = get_service_specific_config(service_name)
        for key, value in overrides.items():
            if hasattr(base_config, key):
                setattr(base_config, key, value)

    return base_config
