"""Tests for LifecycleManager."""

import asyncio
from types import SimpleNamespace

import pytest

from common.process_monitor_helpers.lifecycle import LifecycleManager


@pytest.mark.asyncio
async def test_start_background_scanning_is_idempotent():
    shutdown_event = asyncio.Event()

    async def run_scan_loop():
        await asyncio.sleep(0)

    worker = SimpleNamespace(run_scan_loop=run_scan_loop)
    manager = LifecycleManager(worker, shutdown_event)

    await manager.start_background_scanning(scan_interval_seconds=1)
    first_task = manager._background_task

    await manager.start_background_scanning(scan_interval_seconds=1)
    assert manager._background_task is first_task

    await manager.stop_background_scanning()


@pytest.mark.asyncio
async def test_stop_background_scanning_cancels_on_timeout(monkeypatch):
    shutdown_event = asyncio.Event()
    worker = SimpleNamespace(run_scan_loop=lambda: None)
    manager = LifecycleManager(worker, shutdown_event)
    manager._background_task = SimpleNamespace(  # type: ignore[attr-defined]
        cancelled=False,
        cancel=lambda: setattr(manager._background_task, "cancelled", True),
    )

    def raise_timeout(task, timeout):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(
        "common.process_monitor_helpers.lifecycle.asyncio.wait_for", raise_timeout
    )

    await manager.stop_background_scanning()

    assert manager._background_task is None
