"""Tests for reconnection handler module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.base_connection_manager_helpers.reconnection_handler import ReconnectionHandler


class TestReconnectionHandlerInit:
    """Tests for ReconnectionHandler initialization."""

    def test_initializes_with_parameters(self) -> None:
        """Initializes with all parameters."""
        metrics = MagicMock()

        handler = ReconnectionHandler(
            service_name="test_service",
            initial_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
            max_failures=10,
            metrics_tracker=metrics,
        )

        assert handler.service_name == "test_service"
        assert handler.initial_delay == 1.0
        assert handler.max_delay == 60.0
        assert handler.backoff_multiplier == 2.0
        assert handler.max_failures == 10
        assert handler.metrics_tracker is metrics


class TestReconnectionHandlerCalculateBackoffDelay:
    """Tests for ReconnectionHandler.calculate_backoff_delay."""

    def test_returns_zero_for_no_failures(self) -> None:
        """Returns zero delay when no failures."""
        metrics = MagicMock()
        metrics.get_metrics.return_value = MagicMock(consecutive_failures=0)
        handler = ReconnectionHandler(
            service_name="test_service",
            initial_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
            max_failures=10,
            metrics_tracker=metrics,
        )

        delay = handler.calculate_backoff_delay()

        assert delay == 0.0

    def test_returns_initial_delay_for_first_failure(self) -> None:
        """Returns approximately initial delay for first failure."""
        metrics = MagicMock()
        metrics.get_metrics.return_value = MagicMock(consecutive_failures=1)
        handler = ReconnectionHandler(
            service_name="test_service",
            initial_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
            max_failures=10,
            metrics_tracker=metrics,
        )

        delay = handler.calculate_backoff_delay()

        assert 0.8 <= delay <= 1.2

    def test_applies_exponential_backoff(self) -> None:
        """Applies exponential backoff for subsequent failures."""
        metrics = MagicMock()
        metrics.get_metrics.return_value = MagicMock(consecutive_failures=3)
        handler = ReconnectionHandler(
            service_name="test_service",
            initial_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
            max_failures=10,
            metrics_tracker=metrics,
        )

        delay = handler.calculate_backoff_delay()

        assert 3.2 <= delay <= 4.8

    def test_caps_at_max_delay(self) -> None:
        """Caps delay at max_delay."""
        metrics = MagicMock()
        metrics.get_metrics.return_value = MagicMock(consecutive_failures=10)
        handler = ReconnectionHandler(
            service_name="test_service",
            initial_delay=1.0,
            max_delay=30.0,
            backoff_multiplier=2.0,
            max_failures=15,
            metrics_tracker=metrics,
        )

        delay = handler.calculate_backoff_delay()

        assert delay <= 36.0

    def test_updates_metrics_with_delay(self) -> None:
        """Updates metrics tracker with calculated delay."""
        metrics = MagicMock()
        metrics.get_metrics.return_value = MagicMock(consecutive_failures=1)
        handler = ReconnectionHandler(
            service_name="test_service",
            initial_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
            max_failures=10,
            metrics_tracker=metrics,
        )

        handler.calculate_backoff_delay()

        metrics.set_backoff_delay.assert_called_once()


class TestReconnectionHandlerShouldRetry:
    """Tests for ReconnectionHandler.should_retry."""

    def test_returns_true_when_below_max_failures(self) -> None:
        """Returns True when failures below max."""
        metrics = MagicMock()
        metrics.get_metrics.return_value = MagicMock(consecutive_failures=5)
        handler = ReconnectionHandler(
            service_name="test_service",
            initial_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
            max_failures=10,
            metrics_tracker=metrics,
        )

        assert handler.should_retry() is True

    def test_returns_false_when_at_max_failures(self) -> None:
        """Returns False when at max failures."""
        metrics = MagicMock()
        metrics.get_metrics.return_value = MagicMock(consecutive_failures=10)
        handler = ReconnectionHandler(
            service_name="test_service",
            initial_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
            max_failures=10,
            metrics_tracker=metrics,
        )

        assert handler.should_retry() is False

    def test_returns_false_when_above_max_failures(self) -> None:
        """Returns False when above max failures."""
        metrics = MagicMock()
        metrics.get_metrics.return_value = MagicMock(consecutive_failures=15)
        handler = ReconnectionHandler(
            service_name="test_service",
            initial_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
            max_failures=10,
            metrics_tracker=metrics,
        )

        assert handler.should_retry() is False


class TestReconnectionHandlerApplyBackoff:
    """Tests for ReconnectionHandler.apply_backoff."""

    @pytest.mark.asyncio
    async def test_returns_false_when_no_failures(self) -> None:
        """Returns False without sleeping when no failures."""
        metrics = MagicMock()
        metrics.get_metrics.return_value = MagicMock(consecutive_failures=0)
        handler = ReconnectionHandler(
            service_name="test_service",
            initial_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
            max_failures=10,
            metrics_tracker=metrics,
        )

        result = await handler.apply_backoff()

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_and_sleeps_when_failures(self) -> None:
        """Returns True and sleeps when there are failures."""
        metrics = MagicMock()
        metrics.get_metrics.return_value = MagicMock(consecutive_failures=2)
        handler = ReconnectionHandler(
            service_name="test_service",
            initial_delay=0.01,
            max_delay=60.0,
            backoff_multiplier=2.0,
            max_failures=10,
            metrics_tracker=metrics,
        )

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await handler.apply_backoff()

        assert result is True
        mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_logs_backoff_message(self) -> None:
        """Logs message about backoff delay."""
        metrics = MagicMock()
        metrics.get_metrics.return_value = MagicMock(consecutive_failures=1)
        handler = ReconnectionHandler(
            service_name="test_service",
            initial_delay=0.01,
            max_delay=60.0,
            backoff_multiplier=2.0,
            max_failures=10,
            metrics_tracker=metrics,
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await handler.apply_backoff()
