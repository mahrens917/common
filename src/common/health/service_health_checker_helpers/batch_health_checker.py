"""
Batch health checking and status evaluation logic.

Efficiently checks health of multiple services concurrently,
and evaluates service health based on status values and timestamps.
"""

import asyncio
import logging
import time
from typing import Callable, Coroutine, Dict, List

from ..service_health_types import ServiceHealth, ServiceHealthInfo

logger = logging.getLogger(__name__)

# Constants
_STATUS_STALE_THRESHOLD_SECONDS = 300  # 5 minutes


async def check_all_service_health(
    service_names: List[str],
    check_service_health_func: Callable[[str], Coroutine[None, None, ServiceHealthInfo]],
) -> Dict[str, ServiceHealthInfo]:
    """
    Check health for multiple services efficiently.

    Args:
        service_names: List of service names to check
        check_service_health_func: Async function to check single service health

    Returns:
        Dictionary mapping service name to ServiceHealthInfo
    """
    results = {}

    # Check all service health concurrently
    tasks = [check_service_health_func(service_name) for service_name in service_names]

    health_results = await asyncio.gather(*tasks, return_exceptions=True)

    for service_name, result in zip(service_names, health_results):
        if isinstance(result, Exception):
            logger.error(f"Error checking health for {service_name}: {result}")
            results[service_name] = ServiceHealthInfo(health=ServiceHealth.UNKNOWN, error_message=str(result))
        else:
            results[service_name] = result

    return results


def evaluate_status_health(status_value: str, last_update: float) -> ServiceHealthInfo:
    """
    Evaluate health based on status value and timestamp.

    Args:
        status_value: Service status string
        last_update: Unix timestamp of last status update

    Returns:
        ServiceHealthInfo with evaluated health
    """
    from ...service_status import is_service_failed, is_service_ready

    age_seconds = time.time() - last_update

    if is_service_failed(status_value):
        return ServiceHealthInfo(
            health=ServiceHealth.UNRESPONSIVE,
            last_status_update=last_update,
            error_message=f"Service status: {status_value}",
        )
    elif is_service_ready(status_value):
        if age_seconds < _STATUS_STALE_THRESHOLD_SECONDS:
            return ServiceHealthInfo(health=ServiceHealth.HEALTHY, last_status_update=last_update)
        else:
            return ServiceHealthInfo(
                health=ServiceHealth.DEGRADED,
                last_status_update=last_update,
                error_message=f"Status stale ({age_seconds:.0f}s old)",
            )
    else:
        return ServiceHealthInfo(
            health=ServiceHealth.DEGRADED,
            last_status_update=last_update,
            error_message=f"Unknown status: {status_value}",
        )
