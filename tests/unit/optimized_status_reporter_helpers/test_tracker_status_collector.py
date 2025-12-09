from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.monitoring import ProcessStatus
from src.common.optimized_status_reporter_helpers.tracker_status_collector import (
    TRACKER_STATUS_ERRORS,
    TrackerStatusCollector,
)


@pytest.mark.asyncio
async def test_collect_tracker_status_updates_info_when_running(monkeypatch):
    tracker_info = SimpleNamespace(status=None, pid=None)
    process_manager = SimpleNamespace(process_info={"tracker": tracker_info})
    tracker_controller = MagicMock()
    tracker_controller.get_tracker_status = AsyncMock(
        return_value={"running": True, "pid": 123, "enabled": True}
    )

    collector = TrackerStatusCollector(process_manager, tracker_controller)

    status = await collector.collect_tracker_status()

    assert status["running"] is True
    assert tracker_info.status == ProcessStatus.RUNNING
    assert tracker_info.pid == 123


@pytest.mark.asyncio
async def test_collect_tracker_status_handles_disabled_and_updates_stopped(monkeypatch):
    tracker_info = SimpleNamespace(status=None, pid=321)
    process_manager = SimpleNamespace(process_info={"tracker": tracker_info})
    tracker_controller = MagicMock()
    tracker_controller.get_tracker_status = AsyncMock(
        return_value={"running": False, "pid": None, "enabled": False}
    )

    collector = TrackerStatusCollector(process_manager, tracker_controller)

    status = await collector.collect_tracker_status()

    assert status["running"] is False
    assert tracker_info.status == ProcessStatus.STOPPED
    assert tracker_info.pid is None


@pytest.mark.asyncio
async def test_collect_tracker_status_returns_error_on_exception(caplog):
    tracker_controller = MagicMock()
    tracker_controller.get_tracker_status = AsyncMock(side_effect=RuntimeError("boom"))
    process_manager = SimpleNamespace(process_info={})

    collector = TrackerStatusCollector(process_manager, tracker_controller)
    caplog.set_level("ERROR")

    status = await collector.collect_tracker_status()

    assert status.get("error") == "boom"
    assert "Failed to get tracker status" in caplog.text


def test_merge_tracker_service_state_normalizes():
    collector = TrackerStatusCollector(
        process_manager=SimpleNamespace(process_info={}), tracker_controller=None
    )
    running = [{"name": "deribit"}]
    merged = collector.merge_tracker_service_state(running, {"running": True})
    assert {"name": "tracker"} in merged

    merged = collector.merge_tracker_service_state(
        running + [{"name": "tracker"}], {"running": False}
    )
    assert {"name": "tracker"} not in merged
