from __future__ import annotations

from dataclasses import dataclass

from common.health.health_aggregator_helpers.formatter import StatusFormatter
from common.health.log_activity_monitor import LogActivity, LogActivityStatus


def test_format_log_age_handles_special_statuses() -> None:
    assert StatusFormatter.format_log_age(LogActivity(status=LogActivityStatus.NOT_FOUND)) == "not found"
    assert StatusFormatter.format_log_age(LogActivity(status=LogActivityStatus.ERROR)) == "error"
    assert StatusFormatter.format_log_age(LogActivity(status=LogActivityStatus.RECENT, age_seconds=None)) == "unknown"


def test_format_log_age_formats_seconds_minutes_hours() -> None:
    assert StatusFormatter.format_log_age(LogActivity(status=LogActivityStatus.RECENT, age_seconds=30.9)) == "30s ago"
    assert StatusFormatter.format_log_age(LogActivity(status=LogActivityStatus.RECENT, age_seconds=120.0)) == "2m ago"
    assert StatusFormatter.format_log_age(LogActivity(status=LogActivityStatus.RECENT, age_seconds=7200.0)) == "2h ago"


@dataclass
class _StubServiceHealthResult:
    status_emoji: str
    service_name: str
    status_message: str
    detailed_message: str
    memory_percent: float | None = None


def test_format_status_line_includes_memory_when_present() -> None:
    result = _StubServiceHealthResult(
        status_emoji="✅",
        service_name="svc",
        status_message="ok",
        detailed_message="details",
        memory_percent=12.34,
    )
    formatted = StatusFormatter.format_status_line(result)
    assert " RAM:" in formatted


def test_format_status_line_omits_memory_when_missing() -> None:
    result = _StubServiceHealthResult(
        status_emoji="✅",
        service_name="svc",
        status_message="ok",
        detailed_message="details",
        memory_percent=None,
    )
    formatted = StatusFormatter.format_status_line(result)
    assert " RAM:" not in formatted
