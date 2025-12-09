"""
Clean health monitoring architecture with separated concerns.

This module provides a clear separation between:
- Process monitoring (is the process running?)
- Log activity monitoring (when was the last log entry?)
- Service health checking (is the service responding?)
- Health aggregation (single source of truth for service status)

No more conflated signals or contradictory status reports.
"""

from .health_aggregator import ServiceHealthAggregator
from .health_types import OverallServiceStatus, ServiceHealthResult
from .log_activity_monitor import LogActivity, LogActivityMonitor
from .process_health_monitor import ProcessHealthMonitor, ProcessStatus
from .service_health_checker import ServiceHealthChecker
from .service_health_types import ServiceHealth, ServiceHealthInfo
from .types import BaseHealthMonitor, HealthCheckResult

__all__ = [
    "ProcessHealthMonitor",
    "ProcessStatus",
    "LogActivityMonitor",
    "LogActivity",
    "ServiceHealthChecker",
    "ServiceHealth",
    "ServiceHealthInfo",
    "ServiceHealthAggregator",
    "ServiceHealthResult",
    "OverallServiceStatus",
    "BaseHealthMonitor",
    "HealthCheckResult",
]
