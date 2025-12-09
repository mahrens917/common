"""Tests for state querier module."""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.connection_state_tracker_helpers.state_querier import StateQuerier


class TestStateQuerier:
    """Tests for StateQuerier class."""

    def test_init_stores_store(self) -> None:
        """Stores the provided store reference."""
        mock_store = MagicMock()

        querier = StateQuerier(mock_store)

        assert querier.store is mock_store

    @pytest.mark.asyncio
    async def test_get_connection_state_delegates_to_store(self) -> None:
        """Delegates to store.get_connection_state."""
        mock_store = AsyncMock()
        mock_state = MagicMock()
        mock_store.get_connection_state.return_value = mock_state
        querier = StateQuerier(mock_store)

        result = await querier.get_connection_state("deribit")

        mock_store.get_connection_state.assert_called_once_with("deribit")
        assert result is mock_state

    @pytest.mark.asyncio
    async def test_is_service_in_reconnection_delegates_to_store(self) -> None:
        """Delegates to store.is_service_in_reconnection."""
        mock_store = AsyncMock()
        mock_store.is_service_in_reconnection.return_value = True
        querier = StateQuerier(mock_store)

        result = await querier.is_service_in_reconnection("deribit")

        mock_store.is_service_in_reconnection.assert_called_once_with("deribit")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_services_in_reconnection_delegates_to_store(self) -> None:
        """Delegates to store.get_services_in_reconnection."""
        mock_store = AsyncMock()
        mock_store.get_services_in_reconnection.return_value = ["deribit", "kalshi"]
        querier = StateQuerier(mock_store)

        result = await querier.get_services_in_reconnection()

        mock_store.get_services_in_reconnection.assert_called_once()
        assert result == ["deribit", "kalshi"]

    @pytest.mark.asyncio
    async def test_is_service_in_grace_period_returns_false_for_no_state(self) -> None:
        """Returns False when no state info exists."""
        mock_store = AsyncMock()
        mock_store.get_connection_state.return_value = None
        querier = StateQuerier(mock_store)

        result = await querier.is_service_in_grace_period("deribit")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_service_in_grace_period_returns_true_if_in_reconnection(self) -> None:
        """Returns True when service is in reconnection."""
        mock_store = AsyncMock()
        mock_state = MagicMock()
        mock_state.last_successful_connection = None
        mock_state.in_reconnection = True
        mock_store.get_connection_state.return_value = mock_state
        querier = StateQuerier(mock_store)

        result = await querier.is_service_in_grace_period("deribit")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_service_in_grace_period_returns_true_within_grace(self) -> None:
        """Returns True when within grace period after reconnection."""
        mock_store = AsyncMock()
        mock_state = MagicMock()
        mock_state.last_successful_connection = time.time() - 100
        mock_state.in_reconnection = False
        mock_store.get_connection_state.return_value = mock_state
        querier = StateQuerier(mock_store)

        result = await querier.is_service_in_grace_period("deribit", grace_period_seconds=300)

        assert result is True

    @pytest.mark.asyncio
    async def test_is_service_in_grace_period_returns_false_outside_grace(self) -> None:
        """Returns False when outside grace period."""
        mock_store = AsyncMock()
        mock_state = MagicMock()
        mock_state.last_successful_connection = time.time() - 400
        mock_state.in_reconnection = False
        mock_store.get_connection_state.return_value = mock_state
        querier = StateQuerier(mock_store)

        result = await querier.is_service_in_grace_period("deribit", grace_period_seconds=300)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_reconnection_duration_returns_none_for_no_state(self) -> None:
        """Returns None when no state info exists."""
        mock_store = AsyncMock()
        mock_store.get_connection_state.return_value = None
        querier = StateQuerier(mock_store)

        result = await querier.get_reconnection_duration("deribit")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_reconnection_duration_returns_none_if_not_in_reconnection(self) -> None:
        """Returns None when service is not in reconnection."""
        mock_store = AsyncMock()
        mock_state = MagicMock()
        mock_state.in_reconnection = False
        mock_store.get_connection_state.return_value = mock_state
        querier = StateQuerier(mock_store)

        result = await querier.get_reconnection_duration("deribit")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_reconnection_duration_returns_none_if_no_start_time(self) -> None:
        """Returns None when reconnection_start_time is None."""
        mock_store = AsyncMock()
        mock_state = MagicMock()
        mock_state.in_reconnection = True
        mock_state.reconnection_start_time = None
        mock_store.get_connection_state.return_value = mock_state
        querier = StateQuerier(mock_store)

        result = await querier.get_reconnection_duration("deribit")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_reconnection_duration_returns_duration(self) -> None:
        """Returns duration since reconnection started."""
        mock_store = AsyncMock()
        mock_state = MagicMock()
        mock_state.in_reconnection = True
        mock_state.reconnection_start_time = time.time() - 60
        mock_store.get_connection_state.return_value = mock_state
        querier = StateQuerier(mock_store)

        result = await querier.get_reconnection_duration("deribit")

        assert result is not None
        assert 59 < result < 61

    @pytest.mark.asyncio
    async def test_get_all_connection_states_delegates_to_store(self) -> None:
        """Delegates to store.get_all_connection_states."""
        mock_store = AsyncMock()
        mock_states = {"deribit": MagicMock(), "kalshi": MagicMock()}
        mock_store.get_all_connection_states.return_value = mock_states
        querier = StateQuerier(mock_store)

        result = await querier.get_all_connection_states()

        mock_store.get_all_connection_states.assert_called_once()
        assert result == mock_states
