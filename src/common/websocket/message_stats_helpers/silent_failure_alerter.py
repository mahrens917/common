"""Silent failure detection and alerting for message stats"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def send_silent_failure_alert(service_name: str, time_since_last_update: float) -> None:
    """
    Send alert for silent failure detection.

    Args:
        service_name: Name of the service
        time_since_last_update: Time in seconds since last message

    Note:
        Failures to send alerts are logged but not raised to avoid disrupting monitoring.
    """
    from src.monitor.alerter import Alerter, AlertSeverity

    try:
        alerter = Alerter()
        await alerter.send_alert(
            message=f"🔴 {service_name.upper()}_WS - Silent failure detected - No messages for {time_since_last_update:.1f}s",
            severity=AlertSeverity.CRITICAL,
            alert_type=f"{service_name}_ws_silent_failure",
        )
    except asyncio.CancelledError:
        raise
    except (RuntimeError, ConnectionError, OSError, ValueError):
        logger.exception(f"Failed to send silent failure alert: ")


def check_silent_failure_threshold(
    current_rate: int,
    current_time: float,
    last_nonzero_update_time: float,
    threshold_seconds: int,
    service_name: str,
) -> bool:
    """
    Check if silent failure threshold has been exceeded.

    Args:
        current_rate: Current message rate
        current_time: Current timestamp
        last_nonzero_update_time: Last time a non-zero rate was recorded
        threshold_seconds: Threshold in seconds
        service_name: Service name for logging

    Returns:
        True if threshold exceeded, False otherwise
    """
    if current_rate > 0:
        return False

    time_since_last_update = current_time - last_nonzero_update_time
    if time_since_last_update <= threshold_seconds:
        return False

    error_msg = f"SILENT_FAILURE_DETECTION: No {service_name} messages for {time_since_last_update:.1f}s"
    logger.error(error_msg)
    return True
