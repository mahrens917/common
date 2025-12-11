"""
Batch health checking logic for multiple services.

Efficiently checks health of multiple services concurrently.
"""

import asyncio
import logging
from typing import Callable, Coroutine, Dict, List

from ..service_health_types import ServiceHealth, ServiceHealthInfo

logger = logging.getLogger(__name__)


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
