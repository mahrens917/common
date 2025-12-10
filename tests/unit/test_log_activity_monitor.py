import os
from datetime import datetime, timedelta, timezone

import pytest

from common.health.log_activity_monitor import LogActivityMonitor, LogActivityStatus

_CONST_299 = 299
_CONST_301 = 301


@pytest.mark.asyncio
async def test_log_activity_uses_mtime_when_no_timestamp(tmp_path):
    logs_dir = tmp_path
    log_path = logs_dir / "tracker.log"

    # Create log file without timestamped entries
    log_path.write_text("tracker service booting...\nno timestamp yet\n")

    reference_time = datetime.now(timezone.utc).replace(microsecond=0)
    timestamp = reference_time.timestamp()
    os.utime(log_path, (timestamp, timestamp))

    monitor = LogActivityMonitor(str(logs_dir))
    activity = await monitor.get_log_activity("tracker")

    assert activity.status == LogActivityStatus.RECENT
    assert activity.error_message is None
    assert activity.last_timestamp is not None
    assert abs((activity.last_timestamp - reference_time).total_seconds()) < 1


@pytest.mark.asyncio
async def test_log_activity_reports_not_found_when_missing_log(tmp_path):
    monitor = LogActivityMonitor(str(tmp_path))

    activity = await monitor.get_log_activity("nonexistent_service")

    assert activity.status == LogActivityStatus.NOT_FOUND
    assert activity.error_message is not None


@pytest.mark.asyncio
async def test_log_activity_classifies_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "common.health.log_activity_monitor.env_int",
        lambda key, default=None: {"LOG_RECENT_THRESHOLD": 60, "LOG_STALE_THRESHOLD": 900}.get(
            key, default
        ),
    )

    log_path = tmp_path / "service.log"
    log_path.write_text("booting\n")

    base_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    os.utime(log_path, (base_time.timestamp(), base_time.timestamp()))

    monkeypatch.setattr("common.time_utils.ensure_timezone_aware", lambda dt: dt, raising=False)
    monkeypatch.setattr(
        "common.time_utils.get_current_utc",
        lambda: base_time + timedelta(minutes=5),
        raising=False,
    )

    monitor = LogActivityMonitor(str(tmp_path))
    activity = await monitor.get_log_activity("service")

    assert activity.status == LogActivityStatus.STALE
    assert _CONST_299 <= activity.age_seconds <= _CONST_301


@pytest.mark.asyncio
async def test_log_activity_classifies_old(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "common.health.log_activity_monitor.env_int",
        lambda key, default=None: {"LOG_RECENT_THRESHOLD": 60, "LOG_STALE_THRESHOLD": 600}.get(
            key, default
        ),
    )

    log_path = tmp_path / "trade.log"
    log_path.write_text("started\n")

    base_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    os.utime(log_path, (base_time.timestamp(), base_time.timestamp()))

    monkeypatch.setattr("common.time_utils.ensure_timezone_aware", lambda dt: dt, raising=False)
    monkeypatch.setattr(
        "common.time_utils.get_current_utc",
        lambda: base_time + timedelta(minutes=20),
        raising=False,
    )

    monitor = LogActivityMonitor(str(tmp_path))
    activity = await monitor.get_log_activity("trade")

    assert activity.status == LogActivityStatus.OLD
    assert activity.log_file_path.endswith("trade.log")


@pytest.mark.asyncio
async def test_log_activity_returns_error_when_timestamp_missing(tmp_path, monkeypatch):
    log_path = tmp_path / "service.log"
    log_path.write_text("line\n")

    monitor = LogActivityMonitor(str(tmp_path))
    monkeypatch.setattr(monitor, "_find_most_recent_log_file", lambda pattern: str(log_path))
    monkeypatch.setattr(monitor, "_get_last_log_timestamp", lambda path: None)

    activity = await monitor.get_log_activity("service")

    assert activity.status == LogActivityStatus.ERROR
    assert activity.error_message == "Could not parse timestamp from log file"


@pytest.mark.asyncio
async def test_get_all_service_log_activity(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "common.health.log_activity_monitor.env_int",
        lambda key, default=None: {"LOG_RECENT_THRESHOLD": 10, "LOG_STALE_THRESHOLD": 60}.get(
            key, default
        ),
    )

    base_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    svc_a = tmp_path / "a.log"
    svc_a.write_text("a\n")
    svc_b = tmp_path / "b.log"
    svc_b.write_text("b\n")
    os.utime(svc_a, (base_time.timestamp(), base_time.timestamp()))
    old_time = base_time - timedelta(minutes=2)
    os.utime(svc_b, (old_time.timestamp(), old_time.timestamp()))

    current_time = base_time + timedelta(seconds=5)
    monkeypatch.setattr("common.time_utils.ensure_timezone_aware", lambda dt: dt, raising=False)
    monkeypatch.setattr("common.time_utils.get_current_utc", lambda: current_time, raising=False)

    monitor = LogActivityMonitor(str(tmp_path))
    results = await monitor.get_all_service_log_activity(["a", "b"])

    assert set(results.keys()) == {"a", "b"}
    assert results["a"].status == LogActivityStatus.RECENT
    assert results["b"].status in {LogActivityStatus.STALE, LogActivityStatus.OLD}
