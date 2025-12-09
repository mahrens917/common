"""Tests for context builder."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.common.alert_suppression_manager_helpers.context_builder import ContextBuilder
from src.common.alert_suppression_manager_helpers.time_window_manager import (
    TimeWindowContext,
    TimeWindowManager,
)


@pytest.fixture
def time_window_manager():
    """Create a time window manager for tests."""
    return TimeWindowManager()


@pytest.fixture
def context_builder(time_window_manager):
    """Create a context builder for tests."""
    return ContextBuilder(time_window_manager)


@pytest.mark.asyncio
async def test_context_builder_initialization(time_window_manager):
    """Test context builder initialization."""
    builder = ContextBuilder(time_window_manager)
    assert builder.time_window_manager == time_window_manager


@pytest.mark.asyncio
async def test_build_context_basic(context_builder, monkeypatch):
    """Test building context with basic scenario."""
    time_context = TimeWindowContext(
        is_in_reconnection=False,
        is_in_grace_period=False,
        reconnection_duration=None,
        grace_period_remaining_seconds=None,
    )

    mock_build_time = AsyncMock(return_value=time_context)
    monkeypatch.setattr(context_builder.time_window_manager, "build_time_context", mock_build_time)

    state_tracker = AsyncMock()
    error_classifier = Mock()
    error_classifier.is_reconnection_error_by_type = Mock(return_value=False)

    context = await context_builder.build_context(
        service_name="kalshi",
        service_type="websocket",
        grace_period_seconds=300,
        error_message=None,
        state_tracker=state_tracker,
        error_classifier=error_classifier,
        require_reconnection_error_pattern=True,
    )

    assert context.service_type == "websocket"
    assert context.is_in_reconnection is False
    assert context.is_in_grace_period is False
    assert context.is_reconnection_error is False


@pytest.mark.asyncio
async def test_build_context_with_reconnection_error(context_builder, monkeypatch):
    """Test building context with reconnection error."""
    time_context = TimeWindowContext(
        is_in_reconnection=True,
        is_in_grace_period=False,
        reconnection_duration=45.0,
        grace_period_remaining_seconds=None,
    )

    mock_build_time = AsyncMock(return_value=time_context)
    monkeypatch.setattr(context_builder.time_window_manager, "build_time_context", mock_build_time)

    state_tracker = AsyncMock()
    error_classifier = Mock()
    error_classifier.is_reconnection_error_by_type = Mock(return_value=True)

    context = await context_builder.build_context(
        service_name="weather",
        service_type="websocket",
        grace_period_seconds=300,
        error_message="Connection timeout",
        state_tracker=state_tracker,
        error_classifier=error_classifier,
        require_reconnection_error_pattern=True,
    )

    assert context.service_type == "websocket"
    assert context.is_in_reconnection is True
    assert context.is_reconnection_error is True
    error_classifier.is_reconnection_error_by_type.assert_called_once_with(
        "websocket", "Connection timeout"
    )


@pytest.mark.asyncio
async def test_build_context_no_pattern_requirement(context_builder, monkeypatch):
    """Test building context when pattern matching not required."""
    time_context = TimeWindowContext(
        is_in_reconnection=False,
        is_in_grace_period=True,
        reconnection_duration=None,
        grace_period_remaining_seconds=150.0,
    )

    mock_build_time = AsyncMock(return_value=time_context)
    monkeypatch.setattr(context_builder.time_window_manager, "build_time_context", mock_build_time)

    state_tracker = AsyncMock()
    error_classifier = Mock()

    context = await context_builder.build_context(
        service_name="deribit",
        service_type="rest",
        grace_period_seconds=300,
        error_message="Some error",
        state_tracker=state_tracker,
        error_classifier=error_classifier,
        require_reconnection_error_pattern=False,
    )

    assert context.is_reconnection_error is True
    # Error classifier should not be called when pattern not required
    error_classifier.is_reconnection_error_by_type.assert_not_called()


@pytest.mark.asyncio
async def test_build_context_no_error_message(context_builder, monkeypatch):
    """Test building context with no error message."""
    time_context = TimeWindowContext(
        is_in_reconnection=False,
        is_in_grace_period=False,
        reconnection_duration=None,
        grace_period_remaining_seconds=None,
    )

    mock_build_time = AsyncMock(return_value=time_context)
    monkeypatch.setattr(context_builder.time_window_manager, "build_time_context", mock_build_time)

    state_tracker = AsyncMock()
    error_classifier = Mock()

    context = await context_builder.build_context(
        service_name="kalshi",
        service_type="websocket",
        grace_period_seconds=300,
        error_message=None,
        state_tracker=state_tracker,
        error_classifier=error_classifier,
        require_reconnection_error_pattern=True,
    )

    assert context.is_reconnection_error is False


@pytest.mark.asyncio
async def test_determine_reconnection_error_with_pattern():
    """Test determining reconnection error with pattern matching."""
    builder = ContextBuilder(TimeWindowManager())

    error_classifier = Mock()
    error_classifier.is_reconnection_error_by_type = Mock(return_value=True)

    is_error = builder._determine_reconnection_error(
        error_classifier=error_classifier,
        service_type="websocket",
        error_message="Connection closed",
        require_pattern=True,
    )

    assert is_error is True
    error_classifier.is_reconnection_error_by_type.assert_called_once_with(
        "websocket", "Connection closed"
    )


@pytest.mark.asyncio
async def test_determine_reconnection_error_without_pattern():
    """Test determining reconnection error without pattern matching."""
    builder = ContextBuilder(TimeWindowManager())

    error_classifier = Mock()

    is_error = builder._determine_reconnection_error(
        error_classifier=error_classifier,
        service_type="rest",
        error_message="Any error",
        require_pattern=False,
    )

    assert is_error is True
    error_classifier.is_reconnection_error_by_type.assert_not_called()


@pytest.mark.asyncio
async def test_determine_reconnection_error_no_message():
    """Test determining reconnection error with no message."""
    builder = ContextBuilder(TimeWindowManager())

    error_classifier = Mock()

    is_error = builder._determine_reconnection_error(
        error_classifier=error_classifier,
        service_type="websocket",
        error_message=None,
        require_pattern=True,
    )

    assert is_error is False


@pytest.mark.asyncio
async def test_determine_reconnection_error_classifier_returns_false():
    """Test determining reconnection error when classifier returns False."""
    builder = ContextBuilder(TimeWindowManager())

    error_classifier = Mock()
    error_classifier.is_reconnection_error_by_type = Mock(return_value=False)

    is_error = builder._determine_reconnection_error(
        error_classifier=error_classifier,
        service_type="websocket",
        error_message="Unknown error",
        require_pattern=True,
    )

    assert is_error is False


@pytest.mark.asyncio
async def test_build_context_calls_time_window_manager(context_builder, monkeypatch):
    """Test that build_context calls time window manager correctly."""
    time_context = TimeWindowContext(
        is_in_reconnection=False,
        is_in_grace_period=False,
        reconnection_duration=None,
        grace_period_remaining_seconds=None,
    )

    mock_build_time = AsyncMock(return_value=time_context)
    monkeypatch.setattr(context_builder.time_window_manager, "build_time_context", mock_build_time)

    state_tracker = AsyncMock()
    error_classifier = Mock()
    error_classifier.is_reconnection_error_by_type = Mock(return_value=False)

    await context_builder.build_context(
        service_name="test_service",
        service_type="rest",
        grace_period_seconds=600,
        error_message=None,
        state_tracker=state_tracker,
        error_classifier=error_classifier,
        require_reconnection_error_pattern=True,
    )

    mock_build_time.assert_awaited_once()
    call_kwargs = mock_build_time.call_args.kwargs
    assert call_kwargs["service_name"] == "test_service"
    assert call_kwargs["grace_period_seconds"] == 600
    assert call_kwargs["state_tracker"] == state_tracker
