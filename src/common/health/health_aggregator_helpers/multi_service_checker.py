"""Handle checking multiple services concurrently."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

from ..health_types import ServiceHealthResult
from .result_builder import ResultBuilder

logger = logging.getLogger(__name__)


class MultiServiceChecker:
    """Handle checking multiple services concurrently."""

    def __init__(self, get_single_service_status_func):
        """
        Initialize multi-service checker.

        Args:
            get_single_service_status_func: Function to get status for a single service
        """
        self.get_single_service_status = get_single_service_status_func
        self.result_builder = ResultBuilder()

    async def get_all_service_status(self, service_names: List[str]) -> Dict[str, ServiceHealthResult]:
        """
        Get status for multiple services efficiently.

        Args:
            service_names: List of service names to check

        Returns:
            Dictionary mapping service name to ServiceHealthResult
        """
        # Get all service statuses concurrently
        tasks = [self.get_single_service_status(service_name) for service_name in service_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        status_dict = {}
        for service_name, result in zip(service_names, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to get status for {service_name}: {result}")
                status_dict[service_name] = self.result_builder.build_error_result(service_name, result)
            else:
                status_dict[service_name] = result

        return status_dict
