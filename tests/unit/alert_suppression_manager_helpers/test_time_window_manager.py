"""Tests for time window manager."""

import time
from unittest.mock import AsyncMock, Mock

import pytest

from common.alert_suppression_manager_helpers.time_window_manager import (
    TimeWindowContext,
    TimeWindowManager,
)


@pytest.mark.asyncio
async def test_time_window_context_creation():
    """Test creating TimeWindowContext."""
    context = TimeWindowContext(
        is_in_reconnection=True,
        is_in_grace_period=False,
        reconnection_duration=30.5,
        grace_period_remaining_seconds=None,
    )

    assert context.is_in_reconnection is True
    assert context.is_in_grace_period is False
    assert context.reconnection_duration == 30.5
    assert context.grace_period_remaining_seconds is None


@pytest.mark.asyncio
async def test_build_time_context_not_in_reconnection():
    """Test building context when not in reconnection."""
    state_tracker = AsyncMock()
    state_tracker.is_service_in_reconnection = AsyncMock(return_value=False)
    state_tracker.is_service_in_grace_period = AsyncMock(return_value=False)
    state_tracker.get_reconnection_duration = AsyncMock(return_value=None)

    manager = TimeWindowManager()
    context = await manager.build_time_context(
        service_name="kalshi",
        grace_period_seconds=300,
        state_tracker=state_tracker,
    )

    assert context.is_in_reconnection is False
    assert context.is_in_grace_period is False
    assert context.reconnection_duration is None
    assert context.grace_period_remaining_seconds is None


@pytest.mark.asyncio
async def test_build_time_context_in_reconnection():
    """Test building context when in reconnection."""
    state_tracker = AsyncMock()
    state_tracker.is_service_in_reconnection = AsyncMock(return_value=True)
    state_tracker.is_service_in_grace_period = AsyncMock(return_value=False)
    state_tracker.get_reconnection_duration = AsyncMock(return_value=45.0)

    manager = TimeWindowManager()
    context = await manager.build_time_context(
        service_name="kalshi",
        grace_period_seconds=300,
        state_tracker=state_tracker,
    )

    assert context.is_in_reconnection is True
    assert context.is_in_grace_period is False
    assert context.reconnection_duration == 45.0
    assert context.grace_period_remaining_seconds is None


@pytest.mark.asyncio
async def test_build_time_context_in_grace_period():
    """Test building context when in grace period."""
    connection_state = Mock()
    connection_state.last_successful_connection = time.time() - 100  # 100 seconds ago

    state_tracker = AsyncMock()
    state_tracker.is_service_in_reconnection = AsyncMock(return_value=False)
    state_tracker.is_service_in_grace_period = AsyncMock(return_value=True)
    state_tracker.get_reconnection_duration = AsyncMock(return_value=None)
    state_tracker.get_connection_state = AsyncMock(return_value=connection_state)

    manager = TimeWindowManager()
    context = await manager.build_time_context(
        service_name="weather",
        grace_period_seconds=300,
        state_tracker=state_tracker,
    )

    assert context.is_in_reconnection is False
    assert context.is_in_grace_period is True
    assert context.reconnection_duration is None
    assert context.grace_period_remaining_seconds is not None
    # Should be approximately 200 seconds (300 - 100)
    assert 190 < context.grace_period_remaining_seconds < 210


@pytest.mark.asyncio
async def test_build_time_context_grace_period_no_connection_state():
    """Test building context in grace period when no connection state."""
    state_tracker = AsyncMock()
    state_tracker.is_service_in_reconnection = AsyncMock(return_value=False)
    state_tracker.is_service_in_grace_period = AsyncMock(return_value=True)
    state_tracker.get_reconnection_duration = AsyncMock(return_value=None)
    state_tracker.get_connection_state = AsyncMock(return_value=None)

    manager = TimeWindowManager()
    context = await manager.build_time_context(
        service_name="kalshi",
        grace_period_seconds=300,
        state_tracker=state_tracker,
    )

    assert context.is_in_grace_period is True
    assert context.grace_period_remaining_seconds is None


@pytest.mark.asyncio
async def test_build_time_context_grace_period_no_last_connection():
    """Test building context when in grace period but no last connection time."""
    connection_state = Mock()
    connection_state.last_successful_connection = None

    state_tracker = AsyncMock()
    state_tracker.is_service_in_reconnection = AsyncMock(return_value=False)
    state_tracker.is_service_in_grace_period = AsyncMock(return_value=True)
    state_tracker.get_reconnection_duration = AsyncMock(return_value=None)
    state_tracker.get_connection_state = AsyncMock(return_value=connection_state)

    manager = TimeWindowManager()
    context = await manager.build_time_context(
        service_name="kalshi",
        grace_period_seconds=300,
        state_tracker=state_tracker,
    )

    assert context.is_in_grace_period is True
    assert context.grace_period_remaining_seconds is None


@pytest.mark.asyncio
async def test_build_time_context_grace_period_expired():
    """Test building context when grace period has expired."""
    connection_state = Mock()
    connection_state.last_successful_connection = time.time() - 400  # 400 seconds ago

    state_tracker = AsyncMock()
    state_tracker.is_service_in_reconnection = AsyncMock(return_value=False)
    state_tracker.is_service_in_grace_period = AsyncMock(return_value=True)
    state_tracker.get_reconnection_duration = AsyncMock(return_value=None)
    state_tracker.get_connection_state = AsyncMock(return_value=connection_state)

    manager = TimeWindowManager()
    context = await manager.build_time_context(
        service_name="kalshi",
        grace_period_seconds=300,
        state_tracker=state_tracker,
    )

    assert context.is_in_grace_period is True
    # Should be 0 since grace period expired (300 - 400 = -100, max(0, -100) = 0)
    assert context.grace_period_remaining_seconds == 0.0


@pytest.mark.asyncio
async def test_build_time_context_calls_state_tracker_methods():
    """Test that build_time_context calls all state tracker methods."""
    state_tracker = AsyncMock()
    state_tracker.is_service_in_reconnection = AsyncMock(return_value=False)
    state_tracker.is_service_in_grace_period = AsyncMock(return_value=False)
    state_tracker.get_reconnection_duration = AsyncMock(return_value=None)

    manager = TimeWindowManager()
    await manager.build_time_context(
        service_name="deribit",
        grace_period_seconds=600,
        state_tracker=state_tracker,
    )

    state_tracker.is_service_in_reconnection.assert_awaited_once_with("deribit")
    state_tracker.is_service_in_grace_period.assert_awaited_once_with("deribit", 600)
    state_tracker.get_reconnection_duration.assert_awaited_once_with("deribit")


@pytest.mark.asyncio
async def test_build_time_context_different_grace_periods():
    """Test building context with different grace periods."""
    connection_state = Mock()
    connection_state.last_successful_connection = time.time() - 100

    state_tracker = AsyncMock()
    state_tracker.is_service_in_reconnection = AsyncMock(return_value=False)
    state_tracker.is_service_in_grace_period = AsyncMock(return_value=True)
    state_tracker.get_reconnection_duration = AsyncMock(return_value=None)
    state_tracker.get_connection_state = AsyncMock(return_value=connection_state)

    manager = TimeWindowManager()

    # Test with 200 second grace period
    context1 = await manager.build_time_context(
        service_name="service1",
        grace_period_seconds=200,
        state_tracker=state_tracker,
    )

    # Test with 500 second grace period
    context2 = await manager.build_time_context(
        service_name="service2",
        grace_period_seconds=500,
        state_tracker=state_tracker,
    )

    # Both should be in grace period but with different remaining time
    assert context1.is_in_grace_period is True
    assert context2.is_in_grace_period is True
    assert context1.grace_period_remaining_seconds < context2.grace_period_remaining_seconds
