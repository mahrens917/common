"""
Service status evaluation logic.

Evaluates service health based on status values and timestamps.
"""

import time

from ..service_health_types import ServiceHealth, ServiceHealthInfo

# Constants
_CONST_300 = 300


def evaluate_status_health(status_value: str, last_update: float) -> ServiceHealthInfo:
    """
    Evaluate health based on status value and timestamp.

    Args:
        status_value: Service status string
        last_update: Unix timestamp of last status update

    Returns:
        ServiceHealthInfo with evaluated health
    """
    from ...service_status import is_service_failed, is_service_operational

    age_seconds = time.time() - last_update

    if is_service_failed(status_value):
        return ServiceHealthInfo(
            health=ServiceHealth.UNRESPONSIVE,
            last_status_update=last_update,
            error_message=f"Service status: {status_value}",
        )
    elif is_service_operational(status_value):
        if age_seconds < _CONST_300:  # Status updated within 5 minutes
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
