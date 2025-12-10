"""Additional tests for process discovery helpers."""

from types import SimpleNamespace

import psutil
import pytest

from common.process_killer_helpers.process_discovery import (
    collect_process_candidates,
)


@pytest.mark.asyncio
async def test_collect_process_candidates_returns_filtered(monkeypatch):
    async def fake_query(keywords, service_name):
        return [SimpleNamespace(pid=1, name="python", cmdline=["python", "app"])]

    monkeypatch.setattr(
        "common.process_killer_helpers.monitor_query.query_monitor_for_processes",
        fake_query,
    )

    monkeypatch.setattr(
        "common.process_killer_helpers.process_normalizer.normalize_process",
        lambda raw, service_name: raw,
    )
    monkeypatch.setattr(
        "common.process_killer_helpers.process_filter.filter_processes_by_pid",
        lambda normalized, exclude_pid: ["filtered"] if normalized else [],
    )

    result = await collect_process_candidates(["keyword"], service_name="svc", exclude_pid=None)
    assert result == ["filtered"]


@pytest.mark.asyncio
async def test_collect_process_candidates_falls_back_to_psutil(monkeypatch):
    async def fake_query(*_args, **_kwargs):
        return []

    monkeypatch.setattr(
        "common.process_killer_helpers.monitor_query.query_monitor_for_processes",
        fake_query,
    )

    normalized_calls = []

    def fake_normalize(raw, service_name):
        normalized = SimpleNamespace(pid=raw.pid, name=raw.name, cmdline=raw.cmdline)
        normalized_calls.append(normalized)
        return normalized

    monkeypatch.setattr(
        "common.process_killer_helpers.process_normalizer.normalize_process",
        fake_normalize,
    )

    call_state = {"count": 0}

    def fake_filter(normalized, exclude_pid):
        call_state["count"] += 1
        if call_state["count"] == 1:
            return []
        return normalized

    monkeypatch.setattr(
        "common.process_killer_helpers.process_filter.filter_processes_by_pid",
        fake_filter,
    )

    class DummyProcess:
        def __init__(self, info):
            self.info = info

    monkeypatch.setattr(
        psutil,
        "process_iter",
        lambda fields: [
            DummyProcess({"pid": 99, "cmdline": ["python", "daemon"], "name": "python"}),
        ],
    )

    result = await collect_process_candidates(["python"], service_name="svc", exclude_pid=None)
    assert result
    assert normalized_calls
