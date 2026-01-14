"""Tests for alerter module."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from common.alerter import (
    ALERT_FAILURE_ERRORS,
    Alert,
    Alerter,
    AlerterError,
    AlertSeverity,
)

TEST_MESSAGE = "Test alert message"
TEST_ALERT_TYPE_GENERAL = "general"
TEST_ALERT_TYPE_CUSTOM = "custom"
TEST_CURRENCY_BTC = "BTC"
TEST_CURRENCY_ETH = "ETH"


THROTTLE_WINDOW_SECONDS = 60
MAX_ALERTS_PER_WINDOW = 10


@pytest.fixture
def mock_settings():
    """Create mock alerter settings."""
    settings = MagicMock()
    settings.alerting.throttle_window_seconds = THROTTLE_WINDOW_SECONDS
    settings.alerting.max_alerts_per_window = MAX_ALERTS_PER_WINDOW
    return settings


class TestAlerter:
    """Tests for Alerter class."""

    def test_init_with_settings(self, mock_settings) -> None:
        """Test initialization with settings."""
        alerter = Alerter(mock_settings)

        assert alerter.settings is mock_settings

    def test_init_without_settings(self, mock_settings) -> None:
        """Test initialization without settings gets default."""
        with patch("common.config.shared.get_alerter_settings", return_value=mock_settings):
            alerter = Alerter()

            assert alerter.settings is mock_settings

    @pytest.mark.asyncio
    async def test_send_alert_logs_message(self, mock_settings) -> None:
        """Test send_alert logs the message."""
        alerter = Alerter(mock_settings)

        with patch("common.alerter.logger") as mock_logger:
            result = await alerter.send_alert(TEST_MESSAGE)

            assert result is True
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_send_alert_suppressed(self, mock_settings) -> None:
        """Test send_alert when suppressed."""
        alerter = Alerter(mock_settings)
        alerter.suppression_manager.should_suppress_alert = MagicMock(return_value=True)

        result = await alerter.send_alert(TEST_MESSAGE)

        assert result is True

    @pytest.mark.asyncio
    async def test_send_alert_throttled(self, mock_settings) -> None:
        """Test send_alert when throttled."""
        alerter = Alerter(mock_settings)
        alerter.alert_throttle.record = MagicMock(return_value=False)

        result = await alerter.send_alert(TEST_MESSAGE)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_with_severity(self, mock_settings) -> None:
        """Test send_alert with severity parameter."""
        alerter = Alerter(mock_settings)

        with patch("common.alerter.logger") as mock_logger:
            result = await alerter.send_alert(
                TEST_MESSAGE,
                severity=AlertSeverity.WARNING,
            )

            assert result is True
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_send_chart_image_returns_false(self, mock_settings) -> None:
        """Test send_chart_image returns False (not supported)."""
        alerter = Alerter(mock_settings)

        result = await alerter.send_chart_image("/tmp/chart.png", "Caption")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_chart_returns_false(self, mock_settings) -> None:
        """Test send_chart returns False (not supported)."""
        alerter = Alerter(mock_settings)

        result = await alerter.send_chart("/tmp/chart.png", "Caption")

        assert result is False

    def test_should_send_price_validation_alert(self, mock_settings) -> None:
        """Test should_send_price_validation_alert delegates to tracker."""
        alerter = Alerter(mock_settings)
        alerter.price_tracker.should_send_alert = MagicMock(return_value=True)
        details = {"key": "value"}

        result = alerter.should_send_price_validation_alert(TEST_CURRENCY_BTC, details)

        assert result is True
        alerter.price_tracker.should_send_alert.assert_called_once_with(TEST_CURRENCY_BTC, details)

    def test_clear_price_validation_alert(self, mock_settings) -> None:
        """Test clear_price_validation_alert delegates to tracker."""
        alerter = Alerter(mock_settings)
        alerter.price_tracker.clear_alert = MagicMock(return_value=True)

        result = alerter.clear_price_validation_alert(TEST_CURRENCY_ETH)

        assert result is True
        alerter.price_tracker.clear_alert.assert_called_once_with(TEST_CURRENCY_ETH)

    def test_is_price_validation_alert_active(self, mock_settings) -> None:
        """Test is_price_validation_alert_active delegates to tracker."""
        alerter = Alerter(mock_settings)
        alerter.price_tracker.is_alert_active = MagicMock(return_value=False)

        result = alerter.is_price_validation_alert_active(TEST_CURRENCY_BTC)

        assert result is False
        alerter.price_tracker.is_alert_active.assert_called_once_with(TEST_CURRENCY_BTC)

    @pytest.mark.asyncio
    async def test_cleanup(self, mock_settings) -> None:
        """Test cleanup does nothing."""
        alerter = Alerter(mock_settings)

        await alerter.cleanup()


class TestConstants:
    """Tests for module constants."""

    def test_alert_failure_errors(self) -> None:
        """Test ALERT_FAILURE_ERRORS contains expected error types."""
        assert ConnectionError in ALERT_FAILURE_ERRORS
        assert TimeoutError in ALERT_FAILURE_ERRORS
        assert asyncio.TimeoutError in ALERT_FAILURE_ERRORS
        assert RuntimeError in ALERT_FAILURE_ERRORS


class TestExports:
    """Tests for module exports."""

    def test_all_exports(self) -> None:
        """Test __all__ contains expected exports."""
        from common import alerter

        assert "Alerter" in alerter.__all__
        assert "Alert" in alerter.__all__
        assert "AlertSeverity" in alerter.__all__
        assert "AlerterError" in alerter.__all__
        assert "ALERT_FAILURE_ERRORS" in alerter.__all__
