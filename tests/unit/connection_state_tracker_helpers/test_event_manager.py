"""Unit tests for EventManager class."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.connection_state_tracker_helpers.event_manager import EventManager


class TestEventManagerInit:
    """Tests for EventManager initialization."""

    def test_initializes_with_store(self) -> None:
        """Test that EventManager initializes with a store."""
        mock_store = MagicMock()
        manager = EventManager(store=mock_store)

        assert manager.store is mock_store


class TestRecordConnectionEvent:
    """Tests for record_connection_event method."""

    @pytest.mark.asyncio
    async def test_delegates_to_store(self) -> None:
        """Test that method delegates to store.record_reconnection_event."""
        mock_store = MagicMock()
        mock_store.record_reconnection_event = AsyncMock()
        manager = EventManager(store=mock_store)

        await manager.record_connection_event(
            service_name="test_service", event_type="connected", details="Connection established"
        )

        mock_store.record_reconnection_event.assert_awaited_once_with(
            "test_service", "connected", "Connection established"
        )

    @pytest.mark.asyncio
    async def test_passes_empty_details_by_default(self) -> None:
        """Test that empty details string is passed when not provided."""
        mock_store = MagicMock()
        mock_store.record_reconnection_event = AsyncMock()
        manager = EventManager(store=mock_store)

        await manager.record_connection_event(service_name="test_service", event_type="connected")

        call_args = mock_store.record_reconnection_event.call_args[0]
        assert call_args[2] == ""

    @pytest.mark.asyncio
    async def test_handles_different_event_types(self) -> None:
        """Test recording different event types."""
        mock_store = MagicMock()
        mock_store.record_reconnection_event = AsyncMock()
        manager = EventManager(store=mock_store)

        await manager.record_connection_event(
            service_name="websocket", event_type="disconnected", details="Connection lost"
        )

        mock_store.record_reconnection_event.assert_awaited_once_with(
            "websocket", "disconnected", "Connection lost"
        )

    @pytest.mark.asyncio
    async def test_handles_different_service_names(self) -> None:
        """Test recording events for different services."""
        mock_store = MagicMock()
        mock_store.record_reconnection_event = AsyncMock()
        manager = EventManager(store=mock_store)

        await manager.record_connection_event(
            service_name="kalshi_websocket", event_type="reconnecting"
        )

        call_args = mock_store.record_reconnection_event.call_args[0]
        assert call_args[0] == "kalshi_websocket"


class TestStoreServiceMetrics:
    """Tests for store_service_metrics method."""

    @pytest.mark.asyncio
    async def test_delegates_to_store(self) -> None:
        """Test that method delegates to store.store_service_metrics."""
        mock_store = MagicMock()
        mock_store.store_service_metrics = AsyncMock(return_value=True)
        manager = EventManager(store=mock_store)

        metrics = {"latency_ms": 50, "messages_sent": 100}
        result = await manager.store_service_metrics(service_name="test_service", metrics=metrics)

        mock_store.store_service_metrics.assert_awaited_once_with("test_service", metrics)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_failure(self) -> None:
        """Test that method returns False when store operation fails."""
        mock_store = MagicMock()
        mock_store.store_service_metrics = AsyncMock(return_value=False)
        manager = EventManager(store=mock_store)

        result = await manager.store_service_metrics(
            service_name="test_service", metrics={"count": 1}
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_handles_empty_metrics(self) -> None:
        """Test storing empty metrics dictionary."""
        mock_store = MagicMock()
        mock_store.store_service_metrics = AsyncMock(return_value=True)
        manager = EventManager(store=mock_store)

        result = await manager.store_service_metrics(service_name="test_service", metrics={})

        mock_store.store_service_metrics.assert_awaited_once_with("test_service", {})
        assert result is True

    @pytest.mark.asyncio
    async def test_handles_complex_metrics(self) -> None:
        """Test storing complex metrics with nested structures."""
        mock_store = MagicMock()
        mock_store.store_service_metrics = AsyncMock(return_value=True)
        manager = EventManager(store=mock_store)

        metrics = {
            "latency": {"avg": 45, "max": 120, "min": 10},
            "counts": {"sent": 1000, "received": 950},
            "errors": ["timeout", "connection_reset"],
        }
        result = await manager.store_service_metrics(service_name="websocket", metrics=metrics)

        call_args = mock_store.store_service_metrics.call_args[0]
        assert call_args[1] == metrics
        assert result is True


class TestGetRecentConnectionEvents:
    """Tests for get_recent_connection_events method."""

    @pytest.mark.asyncio
    async def test_delegates_to_store(self) -> None:
        """Test that method delegates to store.get_recent_reconnection_events."""
        mock_store = MagicMock()
        expected_events = [
            {"timestamp": "2025-01-01T10:00:00", "event": "connected"},
            {"timestamp": "2025-01-01T09:30:00", "event": "disconnected"},
        ]
        mock_store.get_recent_reconnection_events = AsyncMock(return_value=expected_events)
        manager = EventManager(store=mock_store)

        result = await manager.get_recent_connection_events(
            service_name="test_service", hours_back=2
        )

        mock_store.get_recent_reconnection_events.assert_awaited_once_with("test_service", 2)
        assert result == expected_events

    @pytest.mark.asyncio
    async def test_uses_default_hours_back(self) -> None:
        """Test that default hours_back of 1 is used when not provided."""
        mock_store = MagicMock()
        mock_store.get_recent_reconnection_events = AsyncMock(return_value=[])
        manager = EventManager(store=mock_store)

        await manager.get_recent_connection_events(service_name="test_service")

        call_args = mock_store.get_recent_reconnection_events.call_args[0]
        assert call_args[1] == 1

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_events(self) -> None:
        """Test that empty list is returned when there are no events."""
        mock_store = MagicMock()
        mock_store.get_recent_reconnection_events = AsyncMock(return_value=[])
        manager = EventManager(store=mock_store)

        result = await manager.get_recent_connection_events(service_name="test_service")

        assert result == []

    @pytest.mark.asyncio
    async def test_handles_different_time_ranges(self) -> None:
        """Test retrieving events with different time ranges."""
        mock_store = MagicMock()
        mock_store.get_recent_reconnection_events = AsyncMock(return_value=[])
        manager = EventManager(store=mock_store)

        await manager.get_recent_connection_events(service_name="kalshi", hours_back=24)

        call_args = mock_store.get_recent_reconnection_events.call_args[0]
        assert call_args[0] == "kalshi"
        assert call_args[1] == 24


class TestCleanupStaleStates:
    """Tests for cleanup_stale_states method."""

    @pytest.mark.asyncio
    async def test_delegates_to_store(self) -> None:
        """Test that method delegates to store.cleanup_stale_states."""
        mock_store = MagicMock()
        mock_store.cleanup_stale_states = AsyncMock(return_value=5)
        manager = EventManager(store=mock_store)

        result = await manager.cleanup_stale_states(max_age_hours=48)

        mock_store.cleanup_stale_states.assert_awaited_once_with(48)
        assert result == 5

    @pytest.mark.asyncio
    async def test_uses_default_max_age_hours(self) -> None:
        """Test that default max_age_hours of 24 is used when not provided."""
        mock_store = MagicMock()
        mock_store.cleanup_stale_states = AsyncMock(return_value=0)
        manager = EventManager(store=mock_store)

        await manager.cleanup_stale_states()

        call_args = mock_store.cleanup_stale_states.call_args[0]
        assert call_args[0] == 24

    @pytest.mark.asyncio
    async def test_returns_count_of_cleaned_states(self) -> None:
        """Test that method returns count of cleaned states."""
        mock_store = MagicMock()
        mock_store.cleanup_stale_states = AsyncMock(return_value=10)
        manager = EventManager(store=mock_store)

        result = await manager.cleanup_stale_states(max_age_hours=12)

        assert result == 10

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_cleanup_needed(self) -> None:
        """Test that method returns 0 when no cleanup is needed."""
        mock_store = MagicMock()
        mock_store.cleanup_stale_states = AsyncMock(return_value=0)
        manager = EventManager(store=mock_store)

        result = await manager.cleanup_stale_states(max_age_hours=1)

        assert result == 0

    @pytest.mark.asyncio
    async def test_handles_different_max_age_values(self) -> None:
        """Test cleanup with different max_age values."""
        mock_store = MagicMock()
        mock_store.cleanup_stale_states = AsyncMock(return_value=3)
        manager = EventManager(store=mock_store)

        await manager.cleanup_stale_states(max_age_hours=72)

        call_args = mock_store.cleanup_stale_states.call_args[0]
        assert call_args[0] == 72
