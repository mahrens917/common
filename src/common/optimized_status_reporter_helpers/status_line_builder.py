"""Status line building helpers."""

from typing import Any, Optional

from src.common.health.log_activity_monitor import LogActivity, LogActivityStatus
from src.common.monitoring import ProcessStatus


def get_status_emoji(running: bool, activity: Optional[LogActivity]) -> str:
    """Get emoji for service status."""
    if running:
        emoji = "🟢"
    else:
        emoji = "🔴"
    if running and activity and activity.status == LogActivityStatus.ERROR:
        emoji = "🟡"
    return emoji


def _resolve_tracker_status(
    running: bool, tracker_status: dict[str, Any], bool_or_default_func
) -> str:
    """Resolve status specifically for tracker service."""
    # Tracker enabled is True if not explicitly set to False
    enabled_raw = tracker_status.get("enabled")
    enabled = bool_or_default_func(enabled_raw, enabled_raw if enabled_raw is not None else True)
    tracker_status["running"] = running
    if running:
        return "Active"
    if not enabled:
        return "Disabled"
    return "Stopped"


def resolve_service_status(
    service_name: str,
    info: Optional[Any],
    running: bool,
    tracker_status: dict[str, Any],
    bool_or_default_func,
) -> str:
    """Resolve display status for a service."""
    if service_name == "tracker":
        return _resolve_tracker_status(running, tracker_status, bool_or_default_func)

    if not info:
        return "Unknown"

    if running:
        return "Active"
    if info.status == ProcessStatus.STOPPED:
        return "Stopped"
    return info.status.value.replace("_", " ").title()
