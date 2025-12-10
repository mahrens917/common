"""Tests for BackgroundScanWorker."""

import asyncio

import psutil
import pytest

from common.process_monitor_helpers.background_worker import BackgroundScanWorker


@pytest.mark.asyncio
async def test_run_scan_loop_exits_on_shutdown_request():
    shutdown_event = asyncio.Event()
    calls = []

    async def perform_incremental_scan():
        calls.append("scan")
        shutdown_event.set()

    worker = BackgroundScanWorker(0, perform_incremental_scan, shutdown_event)

    await worker.run_scan_loop()

    assert calls == ["scan"]


@pytest.mark.asyncio
async def test_run_scan_loop_logs_and_retries_on_errors(monkeypatch):
    shutdown_event = asyncio.Event()
    calls = []

    async def perform_incremental_scan():
        calls.append("scan")
        if len(calls) == 1:
            raise psutil.Error()
        shutdown_event.set()

    sleep_calls = []

    async def fake_sleep(duration):
        sleep_calls.append(duration)

    monkeypatch.setattr(
        "common.process_monitor_helpers.background_worker.asyncio.sleep", fake_sleep
    )
    worker = BackgroundScanWorker(0, perform_incremental_scan, shutdown_event)

    await worker.run_scan_loop()

    assert calls == ["scan", "scan"]
    assert sleep_calls == [0]
