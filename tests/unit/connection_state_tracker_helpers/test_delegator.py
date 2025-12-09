"""Tests for connection_state_tracker_helpers delegator module."""

from __future__ import annotations

import asyncio
from json import JSONDecodeError
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import RedisError

from src.common.connection_state import ConnectionState
from src.common.connection_state_tracker_helpers.delegator import (
    STORE_ERROR_TYPES,
    EventManagerDelegator,
    StateQuerierDelegator,
    StateUpdaterDelegator,
)


class TestStoreErrorTypes:
    """Tests for STORE_ERROR_TYPES constant."""

    def test_contains_expected_error_types(self) -> None:
        """Contains expected error types."""
        assert ConnectionError in STORE_ERROR_TYPES
        assert RedisError in STORE_ERROR_TYPES
        assert RuntimeError in STORE_ERROR_TYPES
        assert asyncio.TimeoutError in STORE_ERROR_TYPES
        assert JSONDecodeError in STORE_ERROR_TYPES


class TestStateUpdaterDelegator:
    """Tests for StateUpdaterDelegator class."""

    def test_init_stores_tracker(self) -> None:
        """Stores tracker reference."""
        mock_tracker = MagicMock()

        delegator = StateUpdaterDelegator(mock_tracker)

        assert delegator.tracker is mock_tracker

    @pytest.mark.asyncio
    async def test_update_connection_state_success(self) -> None:
        """Successfully updates connection state."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_state_updater = AsyncMock()
        mock_state_updater.update_connection_state = AsyncMock(return_value=True)
        mock_tracker.state_updater = mock_state_updater

        delegator = StateUpdaterDelegator(mock_tracker)

        result = await delegator.update_connection_state(
            "kalshi", ConnectionState.CONNECTED, "error context", 3
        )

        assert result is True
        mock_tracker.initialize.assert_called_once()
        mock_state_updater.update_connection_state.assert_called_once_with(
            "kalshi", ConnectionState.CONNECTED, "error context", 3
        )

    @pytest.mark.asyncio
    async def test_update_connection_state_raises_on_redis_error(self) -> None:
        """Raises RuntimeError on RedisError."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_state_updater = AsyncMock()
        mock_state_updater.update_connection_state = AsyncMock(
            side_effect=RedisError("Connection lost")
        )
        mock_tracker.state_updater = mock_state_updater

        delegator = StateUpdaterDelegator(mock_tracker)

        with pytest.raises(RuntimeError) as exc_info:
            await delegator.update_connection_state("kalshi", ConnectionState.CONNECTED)

        assert "Failed to update connection state" in str(exc_info.value)
        assert "kalshi" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_connection_state_raises_on_connection_error(self) -> None:
        """Raises RuntimeError on ConnectionError."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_state_updater = AsyncMock()
        mock_state_updater.update_connection_state = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )
        mock_tracker.state_updater = mock_state_updater

        delegator = StateUpdaterDelegator(mock_tracker)

        with pytest.raises(RuntimeError):
            await delegator.update_connection_state("kalshi", ConnectionState.DISCONNECTED)


class TestStateQuerierDelegator:
    """Tests for StateQuerierDelegator class."""

    def test_init_stores_tracker(self) -> None:
        """Stores tracker reference."""
        mock_tracker = MagicMock()

        delegator = StateQuerierDelegator(mock_tracker)

        assert delegator.tracker is mock_tracker

    @pytest.mark.asyncio
    async def test_get_connection_state_success(self) -> None:
        """Successfully gets connection state."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_state_querier = AsyncMock()
        mock_state_info = MagicMock()
        mock_state_querier.get_connection_state = AsyncMock(return_value=mock_state_info)
        mock_tracker.state_querier = mock_state_querier

        delegator = StateQuerierDelegator(mock_tracker)

        result = await delegator.get_connection_state("kalshi")

        assert result is mock_state_info
        mock_tracker.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_service_in_reconnection_success(self) -> None:
        """Successfully checks reconnection status."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_state_querier = AsyncMock()
        mock_state_querier.is_service_in_reconnection = AsyncMock(return_value=True)
        mock_tracker.state_querier = mock_state_querier

        delegator = StateQuerierDelegator(mock_tracker)

        result = await delegator.is_service_in_reconnection("kalshi")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_service_in_reconnection_raises_on_error(self) -> None:
        """Raises RuntimeError on store error."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_state_querier = AsyncMock()
        mock_state_querier.is_service_in_reconnection = AsyncMock(side_effect=RedisError("Error"))
        mock_tracker.state_querier = mock_state_querier

        delegator = StateQuerierDelegator(mock_tracker)

        with pytest.raises(RuntimeError) as exc_info:
            await delegator.is_service_in_reconnection("kalshi")

        assert "reconnection status" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_is_service_in_grace_period_success(self) -> None:
        """Successfully checks grace period status."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_state_querier = AsyncMock()
        mock_state_querier.is_service_in_grace_period = AsyncMock(return_value=False)
        mock_tracker.state_querier = mock_state_querier

        delegator = StateQuerierDelegator(mock_tracker)

        result = await delegator.is_service_in_grace_period("kalshi", 600)

        assert result is False
        mock_state_querier.is_service_in_grace_period.assert_called_once_with("kalshi", 600)

    @pytest.mark.asyncio
    async def test_get_services_in_reconnection_success(self) -> None:
        """Successfully gets services in reconnection."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_state_querier = AsyncMock()
        mock_state_querier.get_services_in_reconnection = AsyncMock(
            return_value=["kalshi", "deribit"]
        )
        mock_tracker.state_querier = mock_state_querier

        delegator = StateQuerierDelegator(mock_tracker)

        result = await delegator.get_services_in_reconnection()

        assert result == ["kalshi", "deribit"]

    @pytest.mark.asyncio
    async def test_get_services_in_reconnection_raises_on_error(self) -> None:
        """Raises RuntimeError on store error."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_state_querier = AsyncMock()
        mock_state_querier.get_services_in_reconnection = AsyncMock(
            side_effect=RuntimeError("Error")
        )
        mock_tracker.state_querier = mock_state_querier

        delegator = StateQuerierDelegator(mock_tracker)

        with pytest.raises(RuntimeError) as exc_info:
            await delegator.get_services_in_reconnection()

        assert "list services" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_reconnection_duration_success(self) -> None:
        """Successfully gets reconnection duration."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_state_querier = AsyncMock()
        mock_state_querier.get_reconnection_duration = AsyncMock(return_value=45.5)
        mock_tracker.state_querier = mock_state_querier

        delegator = StateQuerierDelegator(mock_tracker)

        result = await delegator.get_reconnection_duration("kalshi")

        assert result == 45.5

    @pytest.mark.asyncio
    async def test_get_reconnection_duration_raises_on_error(self) -> None:
        """Raises RuntimeError on store error."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_state_querier = AsyncMock()
        mock_state_querier.get_reconnection_duration = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_tracker.state_querier = mock_state_querier

        delegator = StateQuerierDelegator(mock_tracker)

        with pytest.raises(RuntimeError) as exc_info:
            await delegator.get_reconnection_duration("kalshi")

        assert "reconnection duration" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_all_connection_states_success(self) -> None:
        """Successfully gets all connection states."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_state_querier = AsyncMock()
        expected_states = {"kalshi": MagicMock(), "deribit": MagicMock()}
        mock_state_querier.get_all_connection_states = AsyncMock(return_value=expected_states)
        mock_tracker.state_querier = mock_state_querier

        delegator = StateQuerierDelegator(mock_tracker)

        result = await delegator.get_all_connection_states()

        assert result == expected_states

    @pytest.mark.asyncio
    async def test_get_all_connection_states_raises_on_error(self) -> None:
        """Raises RuntimeError on store error."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_state_querier = AsyncMock()
        mock_state_querier.get_all_connection_states = AsyncMock(
            side_effect=JSONDecodeError("Error", "", 0)
        )
        mock_tracker.state_querier = mock_state_querier

        delegator = StateQuerierDelegator(mock_tracker)

        with pytest.raises(RuntimeError) as exc_info:
            await delegator.get_all_connection_states()

        assert "load connection states" in str(exc_info.value)


class TestEventManagerDelegator:
    """Tests for EventManagerDelegator class."""

    def test_init_stores_tracker(self) -> None:
        """Stores tracker reference."""
        mock_tracker = MagicMock()

        delegator = EventManagerDelegator(mock_tracker)

        assert delegator.tracker is mock_tracker

    @pytest.mark.asyncio
    async def test_record_connection_event_success(self) -> None:
        """Successfully records connection event."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_event_manager = AsyncMock()
        mock_event_manager.record_connection_event = AsyncMock()
        mock_tracker.event_manager = mock_event_manager

        delegator = EventManagerDelegator(mock_tracker)

        await delegator.record_connection_event("kalshi", "disconnect", "timeout")

        mock_event_manager.record_connection_event.assert_called_once_with(
            "kalshi", "disconnect", "timeout"
        )

    @pytest.mark.asyncio
    async def test_record_connection_event_raises_on_error(self) -> None:
        """Raises RuntimeError on store error."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_event_manager = AsyncMock()
        mock_event_manager.record_connection_event = AsyncMock(side_effect=RedisError("Error"))
        mock_tracker.event_manager = mock_event_manager

        delegator = EventManagerDelegator(mock_tracker)

        with pytest.raises(RuntimeError) as exc_info:
            await delegator.record_connection_event("kalshi", "disconnect")

        assert "record connection event" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_store_service_metrics_success(self) -> None:
        """Successfully stores service metrics."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_event_manager = AsyncMock()
        mock_event_manager.store_service_metrics = AsyncMock(return_value=True)
        mock_tracker.event_manager = mock_event_manager

        delegator = EventManagerDelegator(mock_tracker)

        result = await delegator.store_service_metrics("kalshi", {"latency": 50})

        assert result is True
        mock_event_manager.store_service_metrics.assert_called_once_with("kalshi", {"latency": 50})

    @pytest.mark.asyncio
    async def test_store_service_metrics_raises_on_error(self) -> None:
        """Raises RuntimeError on store error."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_event_manager = AsyncMock()
        mock_event_manager.store_service_metrics = AsyncMock(side_effect=ConnectionError("Error"))
        mock_tracker.event_manager = mock_event_manager

        delegator = EventManagerDelegator(mock_tracker)

        with pytest.raises(RuntimeError) as exc_info:
            await delegator.store_service_metrics("kalshi", {})

        assert "store service metrics" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_recent_connection_events_success(self) -> None:
        """Successfully gets recent events."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_event_manager = AsyncMock()
        expected_events = [{"type": "disconnect"}, {"type": "reconnect"}]
        mock_event_manager.get_recent_connection_events = AsyncMock(return_value=expected_events)
        mock_tracker.event_manager = mock_event_manager

        delegator = EventManagerDelegator(mock_tracker)

        result = await delegator.get_recent_connection_events("kalshi", 2)

        assert result == expected_events
        mock_event_manager.get_recent_connection_events.assert_called_once_with("kalshi", 2)

    @pytest.mark.asyncio
    async def test_get_recent_connection_events_raises_on_error(self) -> None:
        """Raises RuntimeError on store error."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_event_manager = AsyncMock()
        mock_event_manager.get_recent_connection_events = AsyncMock(
            side_effect=RuntimeError("Error")
        )
        mock_tracker.event_manager = mock_event_manager

        delegator = EventManagerDelegator(mock_tracker)

        with pytest.raises(RuntimeError) as exc_info:
            await delegator.get_recent_connection_events("kalshi")

        assert "load connection events" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cleanup_stale_states_success(self) -> None:
        """Successfully cleans up stale states."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_event_manager = AsyncMock()
        mock_event_manager.cleanup_stale_states = AsyncMock(return_value=5)
        mock_tracker.event_manager = mock_event_manager

        delegator = EventManagerDelegator(mock_tracker)

        result = await delegator.cleanup_stale_states(48)

        assert result == 5
        mock_event_manager.cleanup_stale_states.assert_called_once_with(48)

    @pytest.mark.asyncio
    async def test_cleanup_stale_states_raises_on_error(self) -> None:
        """Raises RuntimeError on store error."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_event_manager = AsyncMock()
        mock_event_manager.cleanup_stale_states = AsyncMock(side_effect=RedisError("Error"))
        mock_tracker.event_manager = mock_event_manager

        delegator = EventManagerDelegator(mock_tracker)

        with pytest.raises(RuntimeError) as exc_info:
            await delegator.cleanup_stale_states()

        assert "cleanup stale" in str(exc_info.value)
