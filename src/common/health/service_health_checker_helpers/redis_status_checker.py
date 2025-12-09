"""
Redis-based service status checking logic.

Checks service health by examining Redis status keys.
"""

import logging

from ...redis_protocol.converters import decode_redis_hash
from ...redis_protocol.typing import RedisClient, ensure_awaitable
from ..service_health_types import (
    HEALTH_CHECK_ERRORS,
    MISSING_STATUS_VALUE,
    ServiceHealth,
    ServiceHealthInfo,
)
from .status_evaluator import evaluate_status_health

logger = logging.getLogger(__name__)


async def check_redis_status(service_name: str, redis_client: RedisClient) -> ServiceHealthInfo:
    """
    Check service health via Redis status updates.

    Args:
        service_name: Name of the service
        redis_client: Redis client to use

    Returns:
        ServiceHealthInfo based on Redis status
    """
    try:
        # Get service status from Redis
        status_key = f"status:{service_name}"
        status_data = await ensure_awaitable(redis_client.hgetall(status_key))

        if not status_data:
            return ServiceHealthInfo(
                health=ServiceHealth.UNRESPONSIVE, error_message="No status data in Redis"
            )

        decoded_data = decode_redis_hash(status_data)

        # Parse status information
        status_value = decoded_data.get("status")
        if status_value in (None, ""):
            status_value = MISSING_STATUS_VALUE

        if "timestamp" not in decoded_data:
            return ServiceHealthInfo(
                health=ServiceHealth.UNRESPONSIVE, error_message="No timestamp in status data"
            )
        timestamp_str = decoded_data["timestamp"]

        if not timestamp_str:
            return ServiceHealthInfo(
                health=ServiceHealth.UNRESPONSIVE, error_message="No timestamp in status data"
            )

        try:
            last_update = float(timestamp_str)
            return evaluate_status_health(status_value, last_update)

        except (
            ValueError,
            TypeError,
        ):
            return ServiceHealthInfo(
                health=ServiceHealth.UNRESPONSIVE,
                error_message=f"Invalid timestamp format",
            )

    except HEALTH_CHECK_ERRORS + (
        ValueError,
        TypeError,
        UnicodeDecodeError,
    ):
        logger.debug(f"Redis health check failed for {service_name}")
        return ServiceHealthInfo(health=ServiceHealth.UNKNOWN, error_message=f"Redis check failed")
