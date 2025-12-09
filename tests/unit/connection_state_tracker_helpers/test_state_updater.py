"""Tests for state_updater module."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.connection_state import ConnectionState
from src.common.connection_state_tracker_helpers.state_updater import (
    StateUpdater,
    _compute_timings,
    _is_reconnection_state,
    _record_transition_events,
)
from src.common.redis_protocol.connection_store_helpers.state_processor import (
    ConnectionStateInfo,
)


class TestStateUpdater:
    """Tests for StateUpdater class."""

    def test_init_stores_store(self) -> None:
        """Stores ConnectionStore reference."""
        mock_store = MagicMock()

        updater = StateUpdater(mock_store)

        assert updater.store is mock_store


class TestIsReconnectionState:
    """Tests for _is_reconnection_state function."""

    def test_disconnected_is_reconnection_state(self) -> None:
        """DISCONNECTED is a reconnection state."""
        assert _is_reconnection_state(ConnectionState.DISCONNECTED) is True

    def test_connecting_is_reconnection_state(self) -> None:
        """CONNECTING is a reconnection state."""
        assert _is_reconnection_state(ConnectionState.CONNECTING) is True

    def test_reconnecting_is_reconnection_state(self) -> None:
        """RECONNECTING is a reconnection state."""
        assert _is_reconnection_state(ConnectionState.RECONNECTING) is True

    def test_failed_is_reconnection_state(self) -> None:
        """FAILED is a reconnection state."""
        assert _is_reconnection_state(ConnectionState.FAILED) is True

    def test_connected_is_not_reconnection_state(self) -> None:
        """CONNECTED is not a reconnection state."""
        assert _is_reconnection_state(ConnectionState.CONNECTED) is False

    def test_authenticating_is_not_reconnection_state(self) -> None:
        """AUTHENTICATING is not a reconnection state."""
        assert _is_reconnection_state(ConnectionState.AUTHENTICATING) is False

    def test_authenticated_is_not_reconnection_state(self) -> None:
        """AUTHENTICATED is not a reconnection state."""
        assert _is_reconnection_state(ConnectionState.AUTHENTICATED) is False

    def test_ready_is_not_reconnection_state(self) -> None:
        """READY is not a reconnection state."""
        assert _is_reconnection_state(ConnectionState.READY) is False


class TestComputeTimings:
    """Tests for _compute_timings function."""

    def test_no_existing_state_and_in_reconnection(self) -> None:
        """Sets reconnection_start to current_time when no existing state and entering reconnection."""
        current_time = 1000.0

        reconnection_start, last_success = _compute_timings(
            existing_state=None,
            new_state=ConnectionState.DISCONNECTED,
            in_reconnection=True,
            current_time=current_time,
        )

        assert reconnection_start == 1000.0
        assert last_success is None

    def test_no_existing_state_and_ready(self) -> None:
        """Sets last_success to current_time when no existing state and READY."""
        current_time = 1000.0

        reconnection_start, last_success = _compute_timings(
            existing_state=None,
            new_state=ConnectionState.READY,
            in_reconnection=False,
            current_time=current_time,
        )

        assert reconnection_start is None
        assert last_success == 1000.0

    def test_no_existing_state_and_not_reconnection(self) -> None:
        """Returns None for both when no existing state and not reconnection or ready."""
        current_time = 1000.0

        reconnection_start, last_success = _compute_timings(
            existing_state=None,
            new_state=ConnectionState.CONNECTED,
            in_reconnection=False,
            current_time=current_time,
        )

        assert reconnection_start is None
        assert last_success is None

    def test_existing_state_entering_reconnection(self) -> None:
        """Sets reconnection_start when entering reconnection from non-reconnection state."""
        existing = ConnectionStateInfo(
            service_name="kalshi",
            state=ConnectionState.READY,
            timestamp=900.0,
            in_reconnection=False,
            reconnection_start_time=None,
            error_context=None,
            consecutive_failures=0,
            last_successful_connection=800.0,
        )
        current_time = 1000.0

        reconnection_start, last_success = _compute_timings(
            existing_state=existing,
            new_state=ConnectionState.DISCONNECTED,
            in_reconnection=True,
            current_time=current_time,
        )

        assert reconnection_start == 1000.0
        assert last_success == 800.0

    def test_existing_state_exiting_reconnection_to_ready(self) -> None:
        """Clears reconnection_start and sets last_success when exiting reconnection to READY."""
        existing = ConnectionStateInfo(
            service_name="kalshi",
            state=ConnectionState.RECONNECTING,
            timestamp=900.0,
            in_reconnection=True,
            reconnection_start_time=850.0,
            error_context=None,
            consecutive_failures=2,
            last_successful_connection=700.0,
        )
        current_time = 1000.0

        reconnection_start, last_success = _compute_timings(
            existing_state=existing,
            new_state=ConnectionState.READY,
            in_reconnection=False,
            current_time=current_time,
        )

        assert reconnection_start is None
        assert last_success == 1000.0

    def test_existing_state_staying_in_reconnection(self) -> None:
        """Preserves reconnection_start when staying in reconnection."""
        existing = ConnectionStateInfo(
            service_name="kalshi",
            state=ConnectionState.DISCONNECTED,
            timestamp=900.0,
            in_reconnection=True,
            reconnection_start_time=850.0,
            error_context=None,
            consecutive_failures=1,
            last_successful_connection=700.0,
        )
        current_time = 1000.0

        reconnection_start, last_success = _compute_timings(
            existing_state=existing,
            new_state=ConnectionState.RECONNECTING,
            in_reconnection=True,
            current_time=current_time,
        )

        assert reconnection_start == 850.0
        assert last_success == 700.0


class TestRecordTransitionEvents:
    """Tests for _record_transition_events function."""

    @pytest.mark.asyncio
    async def test_no_events_when_no_existing_state(self) -> None:
        """Does not record events when no existing state."""
        mock_store = MagicMock()
        mock_store.record_reconnection_event = AsyncMock()

        await _record_transition_events(
            store=mock_store,
            service_name="kalshi",
            existing_state=None,
            new_state=ConnectionState.DISCONNECTED,
            in_reconnection=True,
            current_time=1000.0,
        )

        mock_store.record_reconnection_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_records_start_event_when_entering_reconnection(self) -> None:
        """Records start event when entering reconnection."""
        mock_store = MagicMock()
        mock_store.record_reconnection_event = AsyncMock()
        existing = ConnectionStateInfo(
            service_name="kalshi",
            state=ConnectionState.READY,
            timestamp=900.0,
            in_reconnection=False,
            reconnection_start_time=None,
            error_context=None,
            consecutive_failures=0,
            last_successful_connection=800.0,
        )

        await _record_transition_events(
            store=mock_store,
            service_name="kalshi",
            existing_state=existing,
            new_state=ConnectionState.DISCONNECTED,
            in_reconnection=True,
            current_time=1000.0,
        )

        mock_store.record_reconnection_event.assert_called_once_with(
            "kalshi",
            "start",
            "Entering reconnection from ready",
        )

    @pytest.mark.asyncio
    async def test_records_success_event_when_exiting_reconnection(self) -> None:
        """Records success event with elapsed time when exiting reconnection."""
        mock_store = MagicMock()
        mock_store.record_reconnection_event = AsyncMock()
        existing = ConnectionStateInfo(
            service_name="kalshi",
            state=ConnectionState.RECONNECTING,
            timestamp=900.0,
            in_reconnection=True,
            reconnection_start_time=950.0,
            error_context=None,
            consecutive_failures=2,
            last_successful_connection=700.0,
        )

        await _record_transition_events(
            store=mock_store,
            service_name="kalshi",
            existing_state=existing,
            new_state=ConnectionState.READY,
            in_reconnection=False,
            current_time=1000.0,
        )

        mock_store.record_reconnection_event.assert_called_once_with(
            "kalshi",
            "success",
            "Reconnection successful after 50.0s",
        )

    @pytest.mark.asyncio
    async def test_records_success_without_elapsed_when_no_start_time(self) -> None:
        """Records success event without elapsed time when no reconnection_start_time."""
        mock_store = MagicMock()
        mock_store.record_reconnection_event = AsyncMock()
        existing = ConnectionStateInfo(
            service_name="kalshi",
            state=ConnectionState.RECONNECTING,
            timestamp=900.0,
            in_reconnection=True,
            reconnection_start_time=None,
            error_context=None,
            consecutive_failures=2,
            last_successful_connection=700.0,
        )

        await _record_transition_events(
            store=mock_store,
            service_name="kalshi",
            existing_state=existing,
            new_state=ConnectionState.READY,
            in_reconnection=False,
            current_time=1000.0,
        )

        mock_store.record_reconnection_event.assert_called_once_with(
            "kalshi",
            "success",
            "Reconnection successful",
        )

    @pytest.mark.asyncio
    async def test_no_events_when_staying_in_same_reconnection_status(self) -> None:
        """Does not record events when staying in same reconnection status."""
        mock_store = MagicMock()
        mock_store.record_reconnection_event = AsyncMock()
        existing = ConnectionStateInfo(
            service_name="kalshi",
            state=ConnectionState.DISCONNECTED,
            timestamp=900.0,
            in_reconnection=True,
            reconnection_start_time=850.0,
            error_context=None,
            consecutive_failures=1,
            last_successful_connection=700.0,
        )

        await _record_transition_events(
            store=mock_store,
            service_name="kalshi",
            existing_state=existing,
            new_state=ConnectionState.RECONNECTING,
            in_reconnection=True,
            current_time=1000.0,
        )

        mock_store.record_reconnection_event.assert_not_called()


class TestStateUpdaterUpdateConnectionState:
    """Tests for StateUpdater.update_connection_state method."""

    @pytest.mark.asyncio
    async def test_updates_state_successfully(self) -> None:
        """Successfully updates connection state."""
        mock_store = MagicMock()
        mock_store.get_connection_state = AsyncMock(return_value=None)
        mock_store.store_connection_state = AsyncMock(return_value=True)
        mock_store.record_reconnection_event = AsyncMock()

        updater = StateUpdater(mock_store)

        with patch("src.common.connection_state_tracker_helpers.state_updater.time") as mock_time:
            mock_time.time.return_value = 1000.0

            result = await updater.update_connection_state("kalshi", ConnectionState.CONNECTED)

        assert result is True
        mock_store.store_connection_state.assert_called_once()
        state_info = mock_store.store_connection_state.call_args[0][0]
        assert state_info.service_name == "kalshi"
        assert state_info.state == ConnectionState.CONNECTED
        assert state_info.timestamp == 1000.0
        assert state_info.in_reconnection is False

    @pytest.mark.asyncio
    async def test_updates_state_with_error_context(self) -> None:
        """Updates state with error context."""
        mock_store = MagicMock()
        mock_store.get_connection_state = AsyncMock(return_value=None)
        mock_store.store_connection_state = AsyncMock(return_value=True)
        mock_store.record_reconnection_event = AsyncMock()

        updater = StateUpdater(mock_store)

        with patch("src.common.connection_state_tracker_helpers.state_updater.time") as mock_time:
            mock_time.time.return_value = 1000.0

            result = await updater.update_connection_state(
                "kalshi",
                ConnectionState.FAILED,
                error_context="Connection timeout",
                consecutive_failures=3,
            )

        assert result is True
        state_info = mock_store.store_connection_state.call_args[0][0]
        assert state_info.error_context == "Connection timeout"
        assert state_info.consecutive_failures == 3
        assert state_info.in_reconnection is True

    @pytest.mark.asyncio
    async def test_returns_false_when_store_fails(self) -> None:
        """Returns False when store fails."""
        mock_store = MagicMock()
        mock_store.get_connection_state = AsyncMock(return_value=None)
        mock_store.store_connection_state = AsyncMock(return_value=False)
        mock_store.record_reconnection_event = AsyncMock()

        updater = StateUpdater(mock_store)

        with patch("src.common.connection_state_tracker_helpers.state_updater.time") as mock_time:
            mock_time.time.return_value = 1000.0

            result = await updater.update_connection_state("kalshi", ConnectionState.CONNECTED)

        assert result is False

    @pytest.mark.asyncio
    async def test_handles_transition_from_existing_state(self) -> None:
        """Handles transition from existing state."""
        existing = ConnectionStateInfo(
            service_name="kalshi",
            state=ConnectionState.READY,
            timestamp=900.0,
            in_reconnection=False,
            reconnection_start_time=None,
            error_context=None,
            consecutive_failures=0,
            last_successful_connection=800.0,
        )
        mock_store = MagicMock()
        mock_store.get_connection_state = AsyncMock(return_value=existing)
        mock_store.store_connection_state = AsyncMock(return_value=True)
        mock_store.record_reconnection_event = AsyncMock()

        updater = StateUpdater(mock_store)

        with patch("src.common.connection_state_tracker_helpers.state_updater.time") as mock_time:
            mock_time.time.return_value = 1000.0

            result = await updater.update_connection_state("kalshi", ConnectionState.DISCONNECTED)

        assert result is True
        # Should record start event
        mock_store.record_reconnection_event.assert_called_once()
        # State should have reconnection_start_time set
        state_info = mock_store.store_connection_state.call_args[0][0]
        assert state_info.reconnection_start_time == 1000.0
        assert state_info.in_reconnection is True

    @pytest.mark.asyncio
    async def test_handles_reconnection_success(self) -> None:
        """Handles successful reconnection."""
        existing = ConnectionStateInfo(
            service_name="kalshi",
            state=ConnectionState.RECONNECTING,
            timestamp=900.0,
            in_reconnection=True,
            reconnection_start_time=850.0,
            error_context="timeout",
            consecutive_failures=2,
            last_successful_connection=700.0,
        )
        mock_store = MagicMock()
        mock_store.get_connection_state = AsyncMock(return_value=existing)
        mock_store.store_connection_state = AsyncMock(return_value=True)
        mock_store.record_reconnection_event = AsyncMock()

        updater = StateUpdater(mock_store)

        with patch("src.common.connection_state_tracker_helpers.state_updater.time") as mock_time:
            mock_time.time.return_value = 1000.0

            result = await updater.update_connection_state("kalshi", ConnectionState.READY)

        assert result is True
        # Should record success event
        mock_store.record_reconnection_event.assert_called_once_with(
            "kalshi",
            "success",
            "Reconnection successful after 150.0s",
        )
        # State should have reconnection cleared and last_success updated
        state_info = mock_store.store_connection_state.call_args[0][0]
        assert state_info.reconnection_start_time is None
        assert state_info.last_successful_connection == 1000.0
        assert state_info.in_reconnection is False
