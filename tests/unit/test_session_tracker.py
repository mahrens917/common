from __future__ import annotations

import asyncio
import gc
import time
from typing import cast

import aiohttp
import pytest

from common.session_tracker import (
    SessionTracker,
    log_session_diagnostics,
    track_existing_session,
    track_session_close,
    track_session_request,
    tracked_session,
)


class FakeSession:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


def fresh_tracker() -> SessionTracker:
    tracker = SessionTracker.__new__(SessionTracker)
    object.__setattr__(tracker, "_initialized", False)
    SessionTracker.__init__(tracker)
    tracker.sessions = {}
    tracker.session_refs = {}
    tracker._next_session_id = 1
    return tracker


def test_track_session_creation_assigns_id(monkeypatch: pytest.MonkeyPatch):
    tracker = fresh_tracker()
    fake_session = FakeSession()
    session_id = tracker.track_session_creation(cast(aiohttp.ClientSession, fake_session), "service")

    assert session_id == "session_0001"
    assert tracker.sessions[session_id].service_name == "service"
    assert session_id in tracker.session_refs


def test_track_session_activity_increments_request(monkeypatch: pytest.MonkeyPatch):
    tracker = fresh_tracker()
    fake_session = FakeSession()
    session_id = tracker.track_session_creation(cast(aiohttp.ClientSession, fake_session), "svc")

    tracker.track_session_activity(session_id)
    info = tracker.sessions[session_id]
    assert info.request_count == 1
    assert info.last_activity <= time.time()


def test_track_session_closure_marks_closed(monkeypatch: pytest.MonkeyPatch):
    tracker = fresh_tracker()
    fake_session = FakeSession()
    session_id = tracker.track_session_creation(cast(aiohttp.ClientSession, fake_session), "svc")

    tracker.track_session_activity(session_id)
    tracker.track_session_closure(session_id)

    info = tracker.sessions[session_id]
    assert info.is_closed is True
    assert info.closed_at is not None
    assert info.request_count == 1


def test_get_active_sessions_filters_closed(monkeypatch: pytest.MonkeyPatch):
    tracker = fresh_tracker()
    open_session = FakeSession()
    closed_session = FakeSession()

    open_id = tracker.track_session_creation(cast(aiohttp.ClientSession, open_session), "open")
    closed_id = tracker.track_session_creation(cast(aiohttp.ClientSession, closed_session), "closed")

    tracker.track_session_closure(closed_id)
    active = tracker.get_active_sessions()
    assert len(active) == 1
    assert active[0].session_id == open_id


def test_cleanup_old_session_records(monkeypatch: pytest.MonkeyPatch):
    tracker = fresh_tracker()
    session = FakeSession()
    session_id = tracker.track_session_creation(cast(aiohttp.ClientSession, session), "svc")
    tracker.track_session_closure(session_id)

    closed_info = tracker.sessions[session_id]
    assert closed_info.closed_at is not None
    closed_time = closed_info.closed_at
    old_time = closed_time - 1000  # set to far past
    closed_info.closed_at = old_time

    tracker.cleanup_old_session_records(max_age_seconds=10)
    assert session_id not in tracker.sessions


@pytest.mark.asyncio
async def test_tracked_session_context_manager_closes(monkeypatch: pytest.MonkeyPatch):
    tracker = fresh_tracker()
    monkeypatch.setattr("common.session_tracker.session_tracker", tracker)

    async with tracked_session("svc") as (session, session_id):
        assert session_id in tracker.sessions
        assert tracker.sessions[session_id].service_name == "svc"
        track_session_request(session_id)

    info = tracker.sessions[session_id]
    assert info.is_closed is True
    assert info.request_count == 1
    assert session.closed is True


@pytest.mark.asyncio
async def test_tracked_session_closes_existing(monkeypatch: pytest.MonkeyPatch):
    tracker = fresh_tracker()
    monkeypatch.setattr("common.session_tracker.session_tracker", tracker)

    session = aiohttp.ClientSession()
    session_id = track_existing_session(session, "svc")
    track_session_request(session_id)
    track_session_close(session_id)

    info = tracker.sessions[session_id]
    assert info.is_closed is True
    await session.close()


@pytest.mark.asyncio
async def test_log_session_diagnostics(monkeypatch: pytest.MonkeyPatch, caplog):
    tracker = fresh_tracker()
    monkeypatch.setattr("common.session_tracker.session_tracker", tracker)

    session = FakeSession()
    session_id = tracker.track_session_creation(cast(aiohttp.ClientSession, session), "svc")
    track_session_request(session_id)

    await log_session_diagnostics()
    caplog_output = caplog.text
    assert "sessions still active" in caplog_output


@pytest.mark.asyncio
async def test_garbage_collected_session_logs(monkeypatch: pytest.MonkeyPatch, caplog):
    tracker = fresh_tracker()
    session = FakeSession()
    session_id = tracker.track_session_creation(cast(aiohttp.ClientSession, session), "svc")
    tracker.track_session_activity(session_id)

    del session
    gc.collect()
    await asyncio.sleep(0)

    caplog_output = caplog.text
    assert "garbage collected without explicit closure" in caplog_output
