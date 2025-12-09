"""Type definitions for simple health checker."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class HealthStatus(Enum):
    """Simple health status enumeration"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    """Service health information"""

    service_name: str
    status: HealthStatus
    response_time_ms: Optional[float] = None
    last_log_update: Optional[float] = None
    error_message: Optional[str] = None
    activity_status: Optional[str] = None
    seconds_since_last_log: Optional[int] = None
