"""Tests for alerter operations modules."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.alerter_helpers.alert_operations import AlertOperations
from common.alerter_helpers.chart_operations import ChartOperations
from common.alerter_helpers.price_validation_operations import PriceValidationOperations
from common.alerting import AlertSeverity


class TestAlertOperations:
    """Test AlertOperations class."""

    @pytest.mark.asyncio
    async def test_send_alert_when_telegram_enabled(self):
        """Test sending alert when Telegram is enabled."""
        alert_sender = AsyncMock()
        alert_sender.send_alert.return_value = True

        result = await AlertOperations.send_alert(
            telegram_enabled=True,
            alert_sender=alert_sender,
            message="Test message",
            severity=AlertSeverity.INFO,
            alert_type="test",
        )

        assert result is True
        alert_sender.send_alert.assert_called_once_with(
            "Test message",
            AlertSeverity.INFO,
            "test",
            None,
            None,
        )

    @pytest.mark.asyncio
    async def test_send_alert_when_telegram_disabled(self):
        """Test sending alert when Telegram is disabled."""
        alert_sender = AsyncMock()

        result = await AlertOperations.send_alert(
            telegram_enabled=False,
            alert_sender=alert_sender,
            message="Test message",
            severity=AlertSeverity.WARNING,
            alert_type="test",
        )

        assert result is True
        alert_sender.send_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_alert_with_details(self):
        """Test sending alert with additional details."""
        alert_sender = AsyncMock()
        alert_sender.send_alert.return_value = True
        details = {"key": "value"}

        result = await AlertOperations.send_alert(
            telegram_enabled=True,
            alert_sender=alert_sender,
            message="Test message",
            severity=AlertSeverity.CRITICAL,
            alert_type="error_alert",
            details=details,
        )

        assert result is True
        alert_sender.send_alert.assert_called_once_with(
            "Test message",
            AlertSeverity.CRITICAL,
            "error_alert",
            details,
            None,
        )

    @pytest.mark.asyncio
    async def test_send_alert_with_target_user(self):
        """Test sending alert to specific user."""
        alert_sender = AsyncMock()
        alert_sender.send_alert.return_value = True

        result = await AlertOperations.send_alert(
            telegram_enabled=True,
            alert_sender=alert_sender,
            message="Test message",
            severity=AlertSeverity.INFO,
            alert_type="test",
            target_user_id="user123",
        )

        assert result is True
        alert_sender.send_alert.assert_called_once_with(
            "Test message",
            AlertSeverity.INFO,
            "test",
            None,
            "user123",
        )

    @pytest.mark.asyncio
    async def test_send_alert_failure(self):
        """Test handling alert sending failure."""
        alert_sender = AsyncMock()
        alert_sender.send_alert.return_value = False

        result = await AlertOperations.send_alert(
            telegram_enabled=True,
            alert_sender=alert_sender,
            message="Test message",
            severity=AlertSeverity.INFO,
        )

        assert result is False


class TestChartOperations:
    """Test ChartOperations class."""

    @pytest.mark.asyncio
    async def test_send_chart_when_telegram_disabled(self):
        """Test sending chart when Telegram is disabled."""
        delivery_manager = AsyncMock()

        result = await ChartOperations.send_chart_image(
            telegram_enabled=False,
            delivery_manager=delivery_manager,
            authorized_user_ids={"user1", "user2"},
            image_path="/path/chart.png",
        )

        assert result is False
        delivery_manager.send_chart.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_chart_to_authorized_users(self):
        """Test sending chart to all authorized users."""
        delivery_manager = AsyncMock()
        delivery_manager.send_chart.return_value = True

        authorized_users = {"user1", "user2", "user3"}
        result = await ChartOperations.send_chart_image(
            telegram_enabled=True,
            delivery_manager=delivery_manager,
            authorized_user_ids=authorized_users,
            image_path="/path/chart.png",
            caption="Chart caption",
        )

        assert result is True
        delivery_manager.send_chart.assert_called_once()
        call_args = delivery_manager.send_chart.call_args
        assert call_args[0][0] == "/path/chart.png"
        assert call_args[0][1] == "Chart caption"
        # Recipients should be the authorized users
        recipients = call_args[0][2]
        assert set(recipients) == authorized_users

    @pytest.mark.asyncio
    async def test_send_chart_to_target_user(self):
        """Test sending chart to specific target user."""
        delivery_manager = AsyncMock()
        delivery_manager.send_chart.return_value = True

        result = await ChartOperations.send_chart_image(
            telegram_enabled=True,
            delivery_manager=delivery_manager,
            authorized_user_ids={"user1", "user2"},
            image_path="/path/chart.png",
            caption="Chart",
            target_user_id="user_target",
        )

        assert result is True
        delivery_manager.send_chart.assert_called_once_with(
            "/path/chart.png",
            "Chart",
            ["user_target"],
        )

    @pytest.mark.asyncio
    async def test_send_chart_no_authorized_users(self):
        """Test sending chart when no authorized users."""
        delivery_manager = AsyncMock()

        result = await ChartOperations.send_chart_image(
            telegram_enabled=True,
            delivery_manager=delivery_manager,
            authorized_user_ids=set(),
            image_path="/path/chart.png",
        )

        assert result is False
        delivery_manager.send_chart.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_chart_empty_caption(self):
        """Test sending chart with empty caption."""
        delivery_manager = AsyncMock()
        delivery_manager.send_chart.return_value = True

        result = await ChartOperations.send_chart_image(
            telegram_enabled=True,
            delivery_manager=delivery_manager,
            authorized_user_ids={"user1"},
            image_path="/path/chart.png",
            caption="",
        )

        assert result is True
        call_args = delivery_manager.send_chart.call_args
        assert call_args[0][1] == ""

    @pytest.mark.asyncio
    async def test_send_chart_failure(self):
        """Test handling chart sending failure."""
        delivery_manager = AsyncMock()
        delivery_manager.send_chart.return_value = False

        result = await ChartOperations.send_chart_image(
            telegram_enabled=True,
            delivery_manager=delivery_manager,
            authorized_user_ids={"user1"},
            image_path="/path/chart.png",
        )

        assert result is False


class TestPriceValidationOperations:
    """Test PriceValidationOperations class."""

    def test_should_send_alert_telegram_disabled(self):
        """Test should_send_alert when Telegram is disabled."""
        price_tracker = MagicMock()

        result = PriceValidationOperations.should_send_alert(
            telegram_enabled=False,
            price_tracker=price_tracker,
            currency="BTC",
            details={"price": 50000},
        )

        assert result is False
        price_tracker.should_send_alert.assert_not_called()

    def test_should_send_alert_telegram_enabled_positive(self):
        """Test should_send_alert when Telegram enabled and should send."""
        price_tracker = MagicMock()
        price_tracker.should_send_alert.return_value = True

        result = PriceValidationOperations.should_send_alert(
            telegram_enabled=True,
            price_tracker=price_tracker,
            currency="BTC",
            details={"price": 50000},
        )

        assert result is True
        price_tracker.should_send_alert.assert_called_once_with("BTC", {"price": 50000})

    def test_should_send_alert_telegram_enabled_negative(self):
        """Test should_send_alert when Telegram enabled but should not send."""
        price_tracker = MagicMock()
        price_tracker.should_send_alert.return_value = False

        result = PriceValidationOperations.should_send_alert(
            telegram_enabled=True,
            price_tracker=price_tracker,
            currency="ETH",
            details={"price": 3000},
        )

        assert result is False
        price_tracker.should_send_alert.assert_called_once_with("ETH", {"price": 3000})

    def test_clear_alert_telegram_disabled(self):
        """Test clear_alert when Telegram is disabled."""
        price_tracker = MagicMock()

        result = PriceValidationOperations.clear_alert(
            telegram_enabled=False,
            price_tracker=price_tracker,
            currency="BTC",
        )

        assert result is False
        price_tracker.clear_alert.assert_not_called()

    def test_clear_alert_telegram_enabled_success(self):
        """Test clear_alert when Telegram enabled."""
        price_tracker = MagicMock()
        price_tracker.clear_alert.return_value = True

        result = PriceValidationOperations.clear_alert(
            telegram_enabled=True,
            price_tracker=price_tracker,
            currency="BTC",
        )

        assert result is True
        price_tracker.clear_alert.assert_called_once_with("BTC")

    def test_clear_alert_telegram_enabled_failure(self):
        """Test clear_alert failure."""
        price_tracker = MagicMock()
        price_tracker.clear_alert.return_value = False

        result = PriceValidationOperations.clear_alert(
            telegram_enabled=True,
            price_tracker=price_tracker,
            currency="ETH",
        )

        assert result is False
        price_tracker.clear_alert.assert_called_once_with("ETH")

    def test_is_alert_active_telegram_disabled(self):
        """Test is_alert_active when Telegram is disabled."""
        price_tracker = MagicMock()

        result = PriceValidationOperations.is_alert_active(
            telegram_enabled=False,
            price_tracker=price_tracker,
            currency="BTC",
        )

        assert result is False
        price_tracker.is_alert_active.assert_not_called()

    def test_is_alert_active_telegram_enabled_active(self):
        """Test is_alert_active when Telegram enabled and alert is active."""
        price_tracker = MagicMock()
        price_tracker.is_alert_active.return_value = True

        result = PriceValidationOperations.is_alert_active(
            telegram_enabled=True,
            price_tracker=price_tracker,
            currency="BTC",
        )

        assert result is True
        price_tracker.is_alert_active.assert_called_once_with("BTC")

    def test_is_alert_active_telegram_enabled_inactive(self):
        """Test is_alert_active when Telegram enabled and alert is inactive."""
        price_tracker = MagicMock()
        price_tracker.is_alert_active.return_value = False

        result = PriceValidationOperations.is_alert_active(
            telegram_enabled=True,
            price_tracker=price_tracker,
            currency="ETH",
        )

        assert result is False
        price_tracker.is_alert_active.assert_called_once_with("ETH")
