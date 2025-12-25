from __future__ import annotations

"""Standardized service status helpers for lifecycle coordination."""

import json
import logging
import time
from enum import Enum
from typing import Any, Dict

from .redis_protocol.error_types import REDIS_ERRORS
from .redis_protocol.typing import ensure_awaitable
from .redis_utils import RedisOperationError, get_redis_connection

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Standardized service status values for Redis status hash"""

    # Core lifecycle states
    INITIALIZING = "initializing"  # Service is starting up, not ready for requests
    READY = "ready"  # Service is fully operational and ready
    READY_DEGRADED = "ready_degraded"  # Service is ready but in degraded mode (e.g., no external connection)
    STOPPED = "stopped"  # Service has been stopped gracefully

    # Error states
    ERROR = "error"  # Service encountered an error
    FAILED = "failed"  # Service failed to start or operate

    # Transitional states
    STARTING = "starting"  # Service process is starting (before initialization)
    STOPPING = "stopping"  # Service is shutting down
    RESTARTING = "restarting"  # Service is being restarted


class HealthStatus(Enum):
    """Health check status values"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    CRITICAL = "critical"


def create_status_data(status: ServiceStatus, **kwargs) -> Dict[str, Any]:
    """
    Create standardized status data structure for Redis storage.

    Args:
        status: ServiceStatus enum value
        **kwargs: Additional status fields (e.g., error, markets_count, etc.)

    Returns:
        Dictionary with status and timestamp, plus any additional fields
    """
    data = {"status": status.value, "timestamp": time.time()}
    data.update(kwargs)
    return data


def is_service_ready(status_value: str) -> bool:
    """
    Check if a service status indicates the service is ready for operation.
    Includes both fully ready and degraded ready states.

    Args:
        status_value: Status string from Redis

    Returns:
        True if service is ready (including degraded), False otherwise
    """
    return status_value in (ServiceStatus.READY.value, ServiceStatus.READY_DEGRADED.value)


def is_service_operational(status_value: str) -> bool:
    """
    Check if a service status indicates the service is operational.
    Includes READY and READY_DEGRADED states.

    Args:
        status_value: Status string from Redis

    Returns:
        True if service is operational, False otherwise
    """
    return status_value in (ServiceStatus.READY.value, ServiceStatus.READY_DEGRADED.value)


def is_service_failed(status_value: str) -> bool:
    """
    Check if a service status indicates the service has failed.

    Args:
        status_value: Status string from Redis

    Returns:
        True if service has failed, False otherwise
    """
    return status_value in (ServiceStatus.ERROR.value, ServiceStatus.FAILED.value)


STATUS_UPDATE_ERRORS = REDIS_ERRORS + (RedisOperationError, ConnectionError, TypeError, ValueError)


async def set_service_status(service_name: str, status: ServiceStatus, **fields: Any) -> None:
    """Persist a service status update to Redis."""

    detail = create_status_data(status, **fields)

    try:
        redis = await get_redis_connection()
        name_key = str(service_name)
        await ensure_awaitable(redis.hset("status", name_key, status.value))
        detail_key = f"status:{name_key}"
        serialized = {key: json.dumps(value) if isinstance(value, (dict, list)) else str(value) for key, value in detail.items()}
        await ensure_awaitable(redis.hset(detail_key, mapping=serialized))
    except STATUS_UPDATE_ERRORS as exc:
        logger.exception("Failed to update status for %s (%s)", name_key, type(exc).__name__, exc_info=True)
        raise
