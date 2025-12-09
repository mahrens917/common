"""Multi-service health checking."""

import asyncio
from typing import Callable, Coroutine, Dict, List

from .types import HealthStatus, ServiceHealth


class MultiServiceChecker:
    """Checks health for multiple services concurrently."""

    def __init__(
        self,
        check_service_health_fn: Callable[[str], Coroutine[None, None, ServiceHealth]],
    ):
        """
        Initialize multi-service checker.

        Args:
            check_service_health_fn: Function to check health of a single service
        """
        self.check_service_health_fn = check_service_health_fn

    async def check_multiple_services(self, service_names: List[str]) -> Dict[str, ServiceHealth]:
        """
        Check health for multiple services concurrently.

        Args:
            service_names: List of service names to check

        Returns:
            Dictionary mapping service name to ServiceHealth
        """
        tasks = [self.check_service_health_fn(service_name) for service_name in service_names]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        health_status = {}
        for service_name, result in zip(service_names, results):
            if isinstance(result, Exception):
                health_status[service_name] = ServiceHealth(
                    service_name=service_name,
                    status=HealthStatus.UNKNOWN,
                    error_message=str(result),
                )
            else:
                health_status[service_name] = result

        return health_status
