"""Dependency factory for ServiceHealthAggregator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .health_aggregator_helpers import (
    ErrorHandler,
    MultiServiceChecker,
    ResultBuilder,
    StatusAggregator,
    StatusFormatter,
)
from .log_activity_monitor import LogActivityMonitor
from .process_health_monitor import ProcessHealthMonitor
from .service_health_checker import ServiceHealthChecker


@dataclass
class ServiceHealthAggregatorDependencies:
    """Container for ServiceHealthAggregator dependencies."""

    process_monitor: ProcessHealthMonitor
    log_monitor: LogActivityMonitor
    health_checker: ServiceHealthChecker
    error_handler: ErrorHandler
    status_aggregator: StatusAggregator
    result_builder: ResultBuilder
    formatter: StatusFormatter
    multi_checker: MultiServiceChecker


@dataclass(frozen=True)
class OptionalDependencies:
    """Optional dependencies that can be injected."""

    process_monitor: ProcessHealthMonitor | None = None
    log_monitor: LogActivityMonitor | None = None
    health_checker: ServiceHealthChecker | None = None
    error_handler: ErrorHandler | None = None
    status_aggregator: StatusAggregator | None = None
    result_builder: ResultBuilder | None = None
    formatter: StatusFormatter | None = None
    multi_checker: MultiServiceChecker | None = None


SERVICE_HEALTH_DEPENDENCY_FIELDS = (
    "process_monitor",
    "log_monitor",
    "health_checker",
    "error_handler",
    "status_aggregator",
    "result_builder",
    "formatter",
    "multi_checker",
)


class ServiceHealthAggregatorFactory:
    """Factory for creating ServiceHealthAggregator dependencies."""

    @staticmethod
    def create(logs_directory: str, get_service_status_callback) -> ServiceHealthAggregatorDependencies:
        """Create all dependencies for ServiceHealthAggregator."""
        return ServiceHealthAggregatorDependencies(
            process_monitor=ProcessHealthMonitor(),
            log_monitor=LogActivityMonitor(logs_directory),
            health_checker=ServiceHealthChecker(),
            error_handler=ErrorHandler(),
            status_aggregator=StatusAggregator(),
            result_builder=ResultBuilder(),
            formatter=StatusFormatter(),
            multi_checker=MultiServiceChecker(get_service_status_callback),
        )

    @staticmethod
    def _build_from_optional(
        optional_deps: OptionalDependencies,
    ) -> ServiceHealthAggregatorDependencies:
        """Build dependencies from all-provided optional deps."""
        dependencies: dict[str, Any] = {}
        for field in SERVICE_HEALTH_DEPENDENCY_FIELDS:
            value = getattr(optional_deps, field)
            assert value is not None, f"{field} is required for building dependencies"
            dependencies[field] = value
        return ServiceHealthAggregatorDependencies(**dependencies)

    @staticmethod
    def _merge_with_defaults(
        optional_deps: OptionalDependencies,
        defaults: ServiceHealthAggregatorDependencies,
    ) -> ServiceHealthAggregatorDependencies:
        """Merge optional deps with defaults."""
        dependencies: dict[str, Any] = {}
        for field in SERVICE_HEALTH_DEPENDENCY_FIELDS:
            override = getattr(optional_deps, field)
            dependencies[field] = override if override is not None else getattr(defaults, field)
        return ServiceHealthAggregatorDependencies(**dependencies)

    @staticmethod
    def _all_provided(optional_deps: OptionalDependencies) -> bool:
        """Check if all optional dependencies are provided."""
        return all(getattr(optional_deps, field) is not None for field in SERVICE_HEALTH_DEPENDENCY_FIELDS)

    @staticmethod
    def create_or_use(
        logs_directory: str,
        get_service_status_callback,
        optional_deps: OptionalDependencies | None = None,
    ) -> ServiceHealthAggregatorDependencies:
        """Create dependencies only if not all are provided."""
        if optional_deps is None:
            optional_deps = OptionalDependencies()

        if ServiceHealthAggregatorFactory._all_provided(optional_deps):
            return ServiceHealthAggregatorFactory._build_from_optional(optional_deps)

        defaults = ServiceHealthAggregatorFactory.create(logs_directory, get_service_status_callback)
        return ServiceHealthAggregatorFactory._merge_with_defaults(optional_deps, defaults)
