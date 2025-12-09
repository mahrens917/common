"""
Redis pool configuration builder.

Why: Separates configuration assembly from pool creation logic
How: Builds pool settings dict from config values with proper masking
"""

import logging
from typing import Any, Dict

from .. import config

logger = logging.getLogger(__name__)


def build_pool_settings(max_connections: int) -> Dict[str, Any]:
    """
    Build Redis connection pool settings from configuration.

    Args:
        max_connections: Maximum number of connections in pool

    Returns:
        Dictionary of pool settings ready for ConnectionPool constructor
    """
    settings = {
        "host": config.REDIS_HOST,
        "port": config.REDIS_PORT,
        "db": config.REDIS_DB,
        "max_connections": max_connections,
        "decode_responses": True,
        "encoding": "utf-8",
        "socket_timeout": config.REDIS_SOCKET_TIMEOUT,
        "socket_connect_timeout": config.REDIS_SOCKET_CONNECT_TIMEOUT,
        "socket_keepalive": config.REDIS_SOCKET_KEEPALIVE,
        "retry_on_timeout": config.REDIS_RETRY_ON_TIMEOUT,
        "health_check_interval": config.REDIS_HEALTH_CHECK_INTERVAL,
    }

    if config.REDIS_PASSWORD:
        settings["password"] = config.REDIS_PASSWORD

    if config.REDIS_SSL:
        settings["ssl"] = True

    return settings


def mask_sensitive_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a copy of settings with sensitive values masked.

    Args:
        settings: Original settings dictionary

    Returns:
        Dictionary with password masked
    """
    masked = dict(settings)
    if "password" in masked:
        masked["password"] = "***"
    return masked
