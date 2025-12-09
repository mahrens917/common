"""Data types for health aggregator."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .log_activity_monitor import LogActivity
from .process_health_monitor import ProcessHealthInfo
from .service_health_types import ServiceHealthInfo


class OverallServiceStatus(Enum):
    """Clear, non-contradictory service status"""

    HEALTHY = "healthy"
    SILENT = "silent"
    DEGRADED = "degraded"
    UNRESPONSIVE = "unresponsive"
    STOPPED = "stopped"
    NOT_FOUND = "not_found"
    ERROR = "error"


@dataclass
class ServiceHealthResult:
    """Complete service health information"""

    service_name: str
    overall_status: OverallServiceStatus

    # Component statuses
    process_info: ProcessHealthInfo
    log_activity: LogActivity
    service_health: ServiceHealthInfo

    # Display information
    status_emoji: str
    status_message: str
    detailed_message: str

    # Metrics
    memory_percent: Optional[float] = None
    log_age_seconds: Optional[float] = None
