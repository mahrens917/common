"""
Health aggregator - the single source of truth for service status.

Combines signals from process monitoring, log activity, and service health
to provide clear, non-contradictory status reports.
"""

import asyncio
import logging
from typing import Dict, List, Optional

from .health_aggregator_factory import (
    ServiceHealthAggregatorDependencies,
    ServiceHealthAggregatorFactory,
)
from .health_types import ServiceHealthResult

logger = logging.getLogger(__name__)


class ServiceHealthAggregator:
    """
    Single source of truth for service health status.

    Combines process monitoring, log activity, and service health checks
    into clear, non-contradictory status reports.
    """

    def __init__(
        self,
        logs_directory: str = "./logs",
        *,
        dependencies: Optional[ServiceHealthAggregatorDependencies] = None,
    ):
        deps = dependencies or ServiceHealthAggregatorFactory.create(logs_directory, self.get_service_status)
        self.process_monitor = deps.process_monitor
        self.log_monitor = deps.log_monitor
        self.health_checker = deps.health_checker
        self.error_handler = deps.error_handler
        self.status_aggregator = deps.status_aggregator
        self.result_builder = deps.result_builder
        self.formatter = deps.formatter
        self.multi_checker = deps.multi_checker

    async def get_service_status(self, service_name: str) -> ServiceHealthResult:
        """
        Get comprehensive status for a single service.

        Args:
            service_name: Name of the service to check

        Returns:
            ServiceHealthResult with clear, aggregated status
        """
        # Get all component statuses concurrently
        process_task = self.process_monitor.get_process_status(service_name)
        log_task = self.log_monitor.get_log_activity(service_name)
        health_task = self.health_checker.check_service_health(service_name)

        process_result, log_result, service_result = await asyncio.gather(process_task, log_task, health_task, return_exceptions=True)

        process_info = self.error_handler.ensure_process_info(service_name, process_result)
        log_activity = self.error_handler.ensure_log_activity(service_name, log_result)
        service_health = self.error_handler.ensure_service_health(service_name, service_result)

        # Aggregate status using clear decision logic
        overall_status, status_emoji, status_message, detailed_message = self.status_aggregator.aggregate_status(
            service_name, process_info, log_activity, service_health
        )

        from .health_aggregator_helpers.result_builder import HealthResultComponents

        components = HealthResultComponents(
            service_name=service_name,
            overall_status=overall_status,
            process_info=process_info,
            log_activity=log_activity,
            service_health=service_health,
            status_emoji=status_emoji,
            status_message=status_message,
            detailed_message=detailed_message,
        )
        return self.result_builder.build_result(components)

    async def get_all_service_status(self, service_names: List[str]) -> Dict[str, ServiceHealthResult]:
        """
        Get status for multiple services efficiently.

        Args:
            service_names: List of service names to check

        Returns:
            Dictionary mapping service name to ServiceHealthResult
        """
        return await self.multi_checker.get_all_service_status(service_names)

    def format_status_line(self, result: ServiceHealthResult) -> str:
        """
        Format a status line for display (matching existing monitor output).

        Args:
            result: ServiceHealthResult to format

        Returns:
            Formatted status line
        """
        return self.formatter.format_status_line(result)
