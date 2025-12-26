"""Tests for alerter_helpers.alert_sender module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from common.alerter_helpers.alert_sender import (
    AlertDeliveryMixin,
    AlertSender,
    AlertSenderConfig,
)
from common.alerting import Alert, AlertSeverity, AlertThrottle


class TestAlertSenderConfig:
    """Tests for AlertSenderConfig dataclass."""

    def test_stores_all_fields(self) -> None:
        """Test config stores all fields."""
        mock_suppression = MagicMock()
        mock_throttle = MagicMock()
        mock_delivery = MagicMock()
        mock_callback = MagicMock()

        config = AlertSenderConfig(
            suppression_manager=mock_suppression,
            alert_throttle=mock_throttle,
            telegram_enabled=True,
            authorized_user_ids=["123"],
            delivery_manager=mock_delivery,
            ensure_processor_callback=mock_callback,
        )

        assert config.suppression_manager == mock_suppression
        assert config.alert_throttle == mock_throttle
        assert config.telegram_enabled is True
        assert config.authorized_user_ids == ["123"]
        assert config.delivery_manager == mock_delivery
        assert config.ensure_processor_callback == mock_callback


class TestAlertDeliveryMixin:
    """Tests for AlertDeliveryMixin class."""

    def test_should_send_alert_returns_true(self) -> None:
        """Test _should_send_alert returns True when allowed."""

        class TestMixin(AlertDeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.suppression_manager = MagicMock()
        mixin.suppression_manager.should_suppress_alert.return_value = False
        mixin.alert_throttle = MagicMock()
        mixin.alert_throttle.record.return_value = True

        alert = MagicMock()

        result = mixin._should_send_alert(alert, "test_type")

        assert result is True

    def test_should_send_alert_suppressed(self) -> None:
        """Test _should_send_alert returns False when suppressed."""

        class TestMixin(AlertDeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.suppression_manager = MagicMock()
        mixin.suppression_manager.should_suppress_alert.return_value = True
        mixin.alert_throttle = MagicMock()

        alert = MagicMock()

        result = mixin._should_send_alert(alert, "test_type")

        assert result is False

    def test_should_send_alert_throttled(self) -> None:
        """Test _should_send_alert returns False when throttled."""

        class TestMixin(AlertDeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.suppression_manager = MagicMock()
        mixin.suppression_manager.should_suppress_alert.return_value = False
        mixin.alert_throttle = MagicMock()
        mixin.alert_throttle.record.return_value = False

        alert = MagicMock()

        result = mixin._should_send_alert(alert, "test_type")

        assert result is False

    def test_is_suppressed(self) -> None:
        """Test _is_suppressed method."""

        class TestMixin(AlertDeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.suppression_manager = MagicMock()
        mixin.suppression_manager.should_suppress_alert.return_value = True

        result = mixin._is_suppressed("test_type")

        assert result is True

    def test_collect_recipients_with_target(self) -> None:
        """Test _collect_recipients with target user."""

        class TestMixin(AlertDeliveryMixin):
            pass

        mixin = TestMixin()

        result = mixin._collect_recipients("target_user", ["user1", "user2"])

        assert result == ["target_user"]

    def test_collect_recipients_without_target(self) -> None:
        """Test _collect_recipients without target user."""

        class TestMixin(AlertDeliveryMixin):
            pass

        mixin = TestMixin()

        result = mixin._collect_recipients(None, ["user1", "user2"])

        assert result == ["user1", "user2"]

    def test_collect_recipients_empty(self) -> None:
        """Test _collect_recipients with empty authorized list."""

        class TestMixin(AlertDeliveryMixin):
            pass

        mixin = TestMixin()

        result = mixin._collect_recipients(None, [])

        assert result == []

    @pytest.mark.asyncio
    async def test_send_telegram_alert_success(self) -> None:
        """Test _send_telegram_alert success."""

        class TestMixin(AlertDeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.ensure_processor_callback = MagicMock()
        mixin.delivery_manager = MagicMock()
        mixin.delivery_manager.send_alert = AsyncMock(return_value=MagicMock(success=True))
        mixin.authorized_user_ids = ["user1"]

        alert = MagicMock()

        result = await mixin._send_telegram_alert(alert, None)

        assert result is True
        mixin.ensure_processor_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_telegram_alert_no_recipients(self) -> None:
        """Test _send_telegram_alert with no recipients."""

        class TestMixin(AlertDeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.ensure_processor_callback = MagicMock()
        mixin.delivery_manager = MagicMock()
        mixin.authorized_user_ids = []

        alert = MagicMock()

        result = await mixin._send_telegram_alert(alert, None)

        assert result is False

    @pytest.mark.asyncio
    async def test_deliver_telegram_success(self) -> None:
        """Test _deliver_telegram success."""

        class TestMixin(AlertDeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.delivery_manager = MagicMock()
        mixin.delivery_manager.send_alert = AsyncMock(return_value=MagicMock(success=True))

        alert = MagicMock()

        result = await mixin._deliver_telegram(alert, ["user1"])

        assert result is True

    @pytest.mark.asyncio
    async def test_deliver_telegram_failed_result(self) -> None:
        """Test _deliver_telegram with failed result."""

        class TestMixin(AlertDeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.delivery_manager = MagicMock()
        mixin.delivery_manager.send_alert = AsyncMock(return_value=MagicMock(success=False))

        alert = MagicMock()

        result = await mixin._deliver_telegram(alert, ["user1"])

        assert result is False

    @pytest.mark.asyncio
    async def test_deliver_telegram_cancelled(self) -> None:
        """Test _deliver_telegram handles CancelledError."""

        class TestMixin(AlertDeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.delivery_manager = MagicMock()
        mixin.delivery_manager.send_alert = AsyncMock(side_effect=asyncio.CancelledError())

        alert = MagicMock()

        result = await mixin._deliver_telegram(alert, ["user1"])

        assert result is False

    @pytest.mark.asyncio
    async def test_deliver_telegram_runtime_error(self) -> None:
        """Test _deliver_telegram handles RuntimeError."""

        class TestMixin(AlertDeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.delivery_manager = MagicMock()
        mixin.delivery_manager.send_alert = AsyncMock(side_effect=RuntimeError("Error"))
        mixin.suppression_manager = MagicMock()
        mixin.suppression_manager.is_shutdown_in_progress.return_value = False

        alert = MagicMock()

        result = await mixin._deliver_telegram(alert, ["user1"])

        assert result is False

    def test_handle_telegram_exception_during_shutdown(self) -> None:
        """Test _handle_telegram_exception during shutdown."""

        class TestMixin(AlertDeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.suppression_manager = MagicMock()
        mixin.suppression_manager.is_shutdown_in_progress.return_value = True

        result = mixin._handle_telegram_exception(RuntimeError("Error"))

        assert result is False

    def test_handle_telegram_exception_normal(self) -> None:
        """Test _handle_telegram_exception during normal operation."""

        class TestMixin(AlertDeliveryMixin):
            pass

        mixin = TestMixin()
        mixin.suppression_manager = MagicMock()
        mixin.suppression_manager.is_shutdown_in_progress.return_value = False

        result = mixin._handle_telegram_exception(RuntimeError("Error"))

        assert result is False


class TestAlertSenderInit:
    """Tests for AlertSender initialization."""

    def test_init_with_config(self) -> None:
        """Test initialization with config object."""
        mock_suppression = MagicMock()
        mock_throttle = MagicMock(spec=AlertThrottle)
        mock_delivery = MagicMock()
        mock_callback = MagicMock()

        config = AlertSenderConfig(
            suppression_manager=mock_suppression,
            alert_throttle=mock_throttle,
            telegram_enabled=True,
            authorized_user_ids=["123"],
            delivery_manager=mock_delivery,
            ensure_processor_callback=mock_callback,
        )

        sender = AlertSender(config)

        assert sender.suppression_manager == mock_suppression
        assert sender.alert_throttle == mock_throttle
        assert sender.telegram_enabled is True
        assert sender.authorized_user_ids == ["123"]

    def test_init_with_separate_args(self) -> None:
        """Test initialization with separate arguments."""
        mock_suppression = MagicMock()
        mock_throttle = MagicMock(spec=AlertThrottle)

        sender = AlertSender(
            mock_suppression,
            alert_throttle=mock_throttle,
            telegram_enabled=False,
        )

        assert sender.suppression_manager == mock_suppression
        assert sender.alert_throttle == mock_throttle
        assert sender.telegram_enabled is False

    def test_init_raises_without_throttle(self) -> None:
        """Test raises ValueError without throttle."""
        mock_suppression = MagicMock()

        with pytest.raises(ValueError) as exc_info:
            AlertSender(mock_suppression)

        assert "AlertThrottle" in str(exc_info.value)

    def test_init_raises_when_telegram_enabled_without_user_ids(self) -> None:
        """Test raises when Telegram enabled without user IDs."""
        mock_suppression = MagicMock()
        mock_throttle = MagicMock(spec=AlertThrottle)

        with pytest.raises(ValueError) as exc_info:
            AlertSender(
                mock_suppression,
                alert_throttle=mock_throttle,
                telegram_enabled=True,
            )

        assert "user IDs" in str(exc_info.value)

    def test_init_raises_when_telegram_enabled_without_delivery_manager(self) -> None:
        """Test raises when Telegram enabled without delivery manager."""
        mock_suppression = MagicMock()
        mock_throttle = MagicMock(spec=AlertThrottle)

        with pytest.raises(ValueError) as exc_info:
            AlertSender(
                mock_suppression,
                alert_throttle=mock_throttle,
                telegram_enabled=True,
                authorized_user_ids=["123"],
            )

        assert "Delivery manager" in str(exc_info.value)

    def test_init_raises_when_telegram_enabled_without_callback(self) -> None:
        """Test raises when Telegram enabled without processor callback."""
        mock_suppression = MagicMock()
        mock_throttle = MagicMock(spec=AlertThrottle)
        mock_delivery = MagicMock()

        with pytest.raises(ValueError) as exc_info:
            AlertSender(
                mock_suppression,
                alert_throttle=mock_throttle,
                telegram_enabled=True,
                authorized_user_ids=["123"],
                delivery_manager=mock_delivery,
            )

        assert "callback" in str(exc_info.value)


class TestAlertSenderSendAlert:
    """Tests for send_alert method."""

    @pytest.mark.asyncio
    async def test_send_alert_suppressed(self) -> None:
        """Test send_alert when suppressed."""
        mock_suppression = MagicMock()
        mock_suppression.should_suppress_alert.return_value = True
        mock_throttle = MagicMock(spec=AlertThrottle)

        sender = AlertSender(
            mock_suppression,
            alert_throttle=mock_throttle,
            telegram_enabled=False,
        )

        result = await sender.send_alert("Test message")

        assert result is True  # Returns suppression status

    @pytest.mark.asyncio
    async def test_send_alert_throttled(self) -> None:
        """Test send_alert when throttled."""
        mock_suppression = MagicMock()
        mock_suppression.should_suppress_alert.return_value = False
        mock_throttle = MagicMock(spec=AlertThrottle)
        mock_throttle.record.return_value = False

        sender = AlertSender(
            mock_suppression,
            alert_throttle=mock_throttle,
            telegram_enabled=False,
        )

        result = await sender.send_alert("Test message")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_no_channels(self) -> None:
        """Test send_alert with no channels enabled."""
        mock_suppression = MagicMock()
        mock_suppression.should_suppress_alert.return_value = False
        mock_throttle = MagicMock(spec=AlertThrottle)
        mock_throttle.record.return_value = True

        sender = AlertSender(
            mock_suppression,
            alert_throttle=mock_throttle,
            telegram_enabled=False,
        )

        result = await sender.send_alert("Test message")

        assert result is True

    @pytest.mark.asyncio
    async def test_send_alert_via_telegram(self) -> None:
        """Test send_alert via Telegram."""
        mock_suppression = MagicMock()
        mock_suppression.should_suppress_alert.return_value = False
        mock_throttle = MagicMock(spec=AlertThrottle)
        mock_throttle.record.return_value = True
        mock_delivery = MagicMock()
        mock_delivery.send_alert = AsyncMock(return_value=MagicMock(success=True))
        mock_callback = MagicMock()

        sender = AlertSender(
            mock_suppression,
            alert_throttle=mock_throttle,
            telegram_enabled=True,
            authorized_user_ids=["123"],
            delivery_manager=mock_delivery,
            ensure_processor_callback=mock_callback,
        )

        result = await sender.send_alert("Test message", severity=AlertSeverity.WARNING)

        assert result is True
        mock_delivery.send_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_alert_with_details(self) -> None:
        """Test send_alert with details."""
        mock_suppression = MagicMock()
        mock_suppression.should_suppress_alert.return_value = False
        mock_throttle = MagicMock(spec=AlertThrottle)
        mock_throttle.record.return_value = True

        sender = AlertSender(
            mock_suppression,
            alert_throttle=mock_throttle,
            telegram_enabled=False,
        )

        result = await sender.send_alert(
            "Test message",
            severity=AlertSeverity.CRITICAL,
            alert_type="custom",
            details={"key": "value"},
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_send_alert_with_target_user(self) -> None:
        """Test send_alert with target user ID."""
        mock_suppression = MagicMock()
        mock_suppression.should_suppress_alert.return_value = False
        mock_throttle = MagicMock(spec=AlertThrottle)
        mock_throttle.record.return_value = True
        mock_delivery = MagicMock()
        mock_delivery.send_alert = AsyncMock(return_value=MagicMock(success=True))
        mock_callback = MagicMock()

        sender = AlertSender(
            mock_suppression,
            alert_throttle=mock_throttle,
            telegram_enabled=True,
            authorized_user_ids=["123", "456"],
            delivery_manager=mock_delivery,
            ensure_processor_callback=mock_callback,
        )

        result = await sender.send_alert("Test message", target_user_id="789")

        assert result is True
        # Verify only target user received the alert
        call_args = mock_delivery.send_alert.call_args
        assert call_args[0][1] == ["789"]
