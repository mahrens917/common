from unittest.mock import AsyncMock

import pytest

from common.connection_state import ConnectionState
from common.connection_state_tracker import (
    ConnectionStateTracker,
    ConnectionStateTrackerError,
)
from common.redis_protocol.connection_store_helpers.state_processor import (
    ConnectionStateInfo,
)

# from common.redis_protocol.connection_store import ConnectionState  # TODO: Missing or circular import


def make_tracker_with_store(store):
    tracker = ConnectionStateTracker()
    tracker.connection_store = store
    return tracker


def make_store(
    *,
    existing_state=None,
    services_in_reconnection=None,
    reconnection_events=None,
    cleanup_count=0,
):
    store = type(
        "StoreMock",
        (),
        {
            "get_connection_state": AsyncMock(return_value=existing_state),
            "store_connection_state": AsyncMock(return_value=True),
            "record_reconnection_event": AsyncMock(),
            "is_service_in_reconnection": AsyncMock(return_value=False),
            "get_services_in_reconnection": AsyncMock(return_value=services_in_reconnection or []),
            "store_service_metrics": AsyncMock(return_value=True),
            "get_recent_reconnection_events": AsyncMock(return_value=reconnection_events or []),
            "get_all_connection_states": AsyncMock(return_value={}),
            "cleanup_stale_states": AsyncMock(return_value=cleanup_count),
        },
    )()
    return store


@pytest.mark.asyncio
async def test_update_connection_state_sets_last_success_on_ready(monkeypatch):
    store = make_store(existing_state=None)
    tracker = make_tracker_with_store(store)
    monkeypatch.setattr("common.connection_state_tracker.time.time", lambda: 1234.0)

    result = await tracker.update_connection_state("svc", ConnectionState.READY)

    assert result is True
    store.store_connection_state.assert_awaited_once()
    state_info = store.store_connection_state.await_args.args[0]
    assert state_info.last_successful_connection == pytest.approx(1234.0)
    assert state_info.in_reconnection is False
    store.record_reconnection_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_connection_state_records_reconnection_start(monkeypatch):
    existing = ConnectionStateInfo(
        service_name="svc",
        state=ConnectionState.READY,
        timestamp=100.0,
        in_reconnection=False,
        reconnection_start_time=None,
        last_successful_connection=90.0,
    )
    store = make_store(existing_state=existing)
    tracker = make_tracker_with_store(store)
    monkeypatch.setattr("common.connection_state_tracker.time.time", lambda: 200.0)

    await tracker.update_connection_state("svc", ConnectionState.RECONNECTING)

    store.record_reconnection_event.assert_awaited_once()
    args = store.record_reconnection_event.await_args.args
    assert args[0] == "svc"
    assert args[1] == "start"
    stored_state = store.store_connection_state.await_args.args[0]
    assert stored_state.in_reconnection is True
    assert stored_state.reconnection_start_time == pytest.approx(200.0)


@pytest.mark.asyncio
async def test_update_connection_state_records_reconnection_success(monkeypatch):
    existing = ConnectionStateInfo(
        service_name="svc",
        state=ConnectionState.RECONNECTING,
        timestamp=50.0,
        in_reconnection=True,
        reconnection_start_time=25.0,
        last_successful_connection=None,
    )
    store = make_store(existing_state=existing)
    tracker = make_tracker_with_store(store)
    monkeypatch.setattr("common.connection_state_tracker.time.time", lambda: 80.0)

    await tracker.update_connection_state("svc", ConnectionState.READY)

    store.record_reconnection_event.assert_awaited_once()
    args = store.record_reconnection_event.await_args.args
    assert args[1] == "success"
    assert "55.0s" in args[2]
    stored_state = store.store_connection_state.await_args.args[0]
    assert stored_state.last_successful_connection == pytest.approx(80.0)
    assert stored_state.reconnection_start_time is None


@pytest.mark.asyncio
async def test_is_service_in_grace_period_checks_last_success(monkeypatch):
    state = ConnectionStateInfo(
        service_name="svc",
        state=ConnectionState.READY,
        timestamp=0.0,
        in_reconnection=False,
        reconnection_start_time=None,
        last_successful_connection=100.0,
    )
    store = make_store(existing_state=state)
    tracker = make_tracker_with_store(store)
    monkeypatch.setattr("common.connection_state_tracker.time.time", lambda: 120.0)

    result = await tracker.is_service_in_grace_period("svc", grace_period_seconds=30)

    assert result is True


@pytest.mark.asyncio
async def test_is_service_in_grace_period_true_when_in_reconnection(monkeypatch):
    state = ConnectionStateInfo(
        service_name="svc",
        state=ConnectionState.RECONNECTING,
        timestamp=0.0,
        in_reconnection=True,
        reconnection_start_time=10.0,
        last_successful_connection=None,
    )
    store = make_store(existing_state=state)
    tracker = make_tracker_with_store(store)
    monkeypatch.setattr("common.connection_state_tracker.time.time", lambda: 100.0)

    result = await tracker.is_service_in_grace_period("svc")

    assert result is True


@pytest.mark.asyncio
async def test_get_reconnection_duration_calculates_elapsed(monkeypatch):
    state = ConnectionStateInfo(
        service_name="svc",
        state=ConnectionState.RECONNECTING,
        timestamp=0.0,
        in_reconnection=True,
        reconnection_start_time=50.0,
    )
    store = make_store(existing_state=state)
    tracker = make_tracker_with_store(store)
    monkeypatch.setattr("common.connection_state_tracker.time.time", lambda: 80.0)

    duration = await tracker.get_reconnection_duration("svc")

    assert duration == pytest.approx(30.0)


@pytest.mark.asyncio
async def test_initialize_raises_runtime_error_on_failure(monkeypatch):
    async def failing_get_store():
        raise ValueError("redis unavailable")

    monkeypatch.setattr(
        "common.connection_state_tracker.get_connection_store", failing_get_store
    )

    tracker = ConnectionStateTracker()
    with pytest.raises(ValueError, match="redis unavailable"):
        await tracker.initialize()


def test_require_store_raises_when_uninitialized():
    tracker = ConnectionStateTracker()
    with pytest.raises(RuntimeError, match="Connection store not initialized"):
        tracker._require_store()


@pytest.mark.asyncio
async def test_get_services_in_reconnection_handles_error(monkeypatch):
    store = make_store()
    store.get_services_in_reconnection.side_effect = Exception("boom")
    tracker = make_tracker_with_store(store)

    with pytest.raises(Exception, match="boom"):
        await tracker.get_services_in_reconnection()


@pytest.mark.asyncio
async def test_store_service_metrics_returns_false_on_error():
    store = make_store()
    store.store_service_metrics.side_effect = Exception("fail")
    tracker = make_tracker_with_store(store)

    with pytest.raises(Exception, match="fail"):
        await tracker.store_service_metrics("svc", {"metric": 1})


@pytest.mark.asyncio
async def test_record_connection_event_swallows_store_errors():
    store = make_store()
    store.record_reconnection_event.side_effect = Exception("fail")
    tracker = make_tracker_with_store(store)

    with pytest.raises(Exception, match="fail"):
        await tracker.record_connection_event("svc", "start", "details")


@pytest.mark.asyncio
async def test_cleanup_stale_states_returns_zero_on_error():
    store = make_store()
    store.cleanup_stale_states.side_effect = Exception("fail")
    tracker = make_tracker_with_store(store)

    with pytest.raises(Exception, match="fail"):
        await tracker.cleanup_stale_states()


@pytest.mark.asyncio
async def test_update_connection_state_returns_false_on_store_error():
    store = make_store()
    store.store_connection_state.side_effect = Exception("fail")
    tracker = make_tracker_with_store(store)

    with pytest.raises(Exception, match="fail"):
        await tracker.update_connection_state("svc", ConnectionState.READY)


@pytest.mark.asyncio
async def test_is_service_in_reconnection_handles_store_error():
    store = make_store()
    store.is_service_in_reconnection.side_effect = Exception("boom")
    tracker = make_tracker_with_store(store)

    with pytest.raises(Exception, match="boom"):
        await tracker.is_service_in_reconnection("svc")


@pytest.mark.asyncio
async def test_get_all_connection_states_returns_empty_on_error():
    store = make_store()
    store.get_all_connection_states.side_effect = Exception("redis issue")
    tracker = make_tracker_with_store(store)

    with pytest.raises(Exception, match="redis issue"):
        await tracker.get_all_connection_states()


@pytest.mark.asyncio
async def test_get_recent_connection_events_handles_errors():
    store = make_store()
    store.get_recent_reconnection_events.side_effect = Exception("boom")
    tracker = make_tracker_with_store(store)

    with pytest.raises(Exception, match="boom"):
        await tracker.get_recent_connection_events("svc")


@pytest.mark.asyncio
async def test_is_service_in_grace_period_returns_false_on_error():
    store = make_store()
    store.get_connection_state.side_effect = Exception("redis down")
    tracker = make_tracker_with_store(store)

    with pytest.raises(Exception, match="redis down"):
        await tracker.is_service_in_grace_period("svc")
