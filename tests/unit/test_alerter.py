"""Tests for alerter module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.alerter import (
    ALERT_FAILURE_ERRORS,
    Alert,
    AlertDispatchMixin,
    Alerter,
    AlerterError,
    AlertSeverity,
    CommandHandlersMixin,
    PendingTelegramMedia,
    PendingTelegramMessage,
    PriceValidationMixin,
    QueuedCommand,
    RateLimitMixin,
    TelegramDeliveryResult,
    _send_alert,
)

# Test constants
TEST_MESSAGE = "Test alert message"
TEST_MESSAGE_WARNING = "Warning alert message"
TEST_MESSAGE_CRITICAL = "Critical alert message"
TEST_CAPTION = "Test caption"
TEST_IMAGE_PATH = "/tmp/test_chart.png"
TEST_IMAGE_PATH_ALT = "/tmp/alternate_chart.png"
TEST_USER_ID = "123456"
TEST_USER_ID_ALT = "789012"
TEST_COMMAND_HELP = "help"
TEST_COMMAND_LOAD = "load"
TEST_COMMAND_PRICE = "price"
TEST_COMMAND_TEMP = "temp"
TEST_COMMAND_PNL = "pnl"
TEST_COMMAND_CUSTOM = "custom"
TEST_ALERT_TYPE_GENERAL = "general"
TEST_ALERT_TYPE_CUSTOM = "custom"
TEST_CURRENCY_BTC = "BTC"
TEST_CURRENCY_ETH = "ETH"
TEST_THROTTLE_WINDOW = 60
TEST_MAX_ALERTS = 10
TEST_BACKOFF_SECONDS = 30
TEST_429_COUNT = 5
TEST_TIMESTAMP = 1234567890.0


class TestAlertDispatchMixinSendAlert:
    """Tests for AlertDispatchMixin send_alert method."""

    @pytest.mark.asyncio
    async def test_send_alert_delegates_to_send_alert_function(self) -> None:
        """Test send_alert delegates to _send_alert function."""

        class TestMixin(AlertDispatchMixin):
            telegram_enabled = False
            delivery_manager = None
            authorized_user_ids = None
            alert_throttle = None
            command_processor = None

        mixin = TestMixin()

        with patch("common.alerter._send_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await mixin.send_alert(TEST_MESSAGE)

            assert result is True
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert args[0] is mixin
            assert args[1] == TEST_MESSAGE
            assert args[2] == AlertSeverity.INFO
            assert args[3] == TEST_ALERT_TYPE_GENERAL
            assert args[4] is None
            assert args[5] is None

    @pytest.mark.asyncio
    async def test_send_alert_with_all_parameters(self) -> None:
        """Test send_alert with all parameters."""

        class TestMixin(AlertDispatchMixin):
            telegram_enabled = False
            delivery_manager = None
            authorized_user_ids = None
            alert_throttle = None
            command_processor = None

        mixin = TestMixin()
        details = {"key": "value"}

        with patch("common.alerter._send_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            result = await mixin.send_alert(
                TEST_MESSAGE_WARNING,
                severity=AlertSeverity.WARNING,
                alert_type=TEST_ALERT_TYPE_CUSTOM,
                details=details,
                target_user_id=TEST_USER_ID,
            )

            assert result is True
            args = mock_send.call_args[0]
            assert args[1] == TEST_MESSAGE_WARNING
            assert args[2] == AlertSeverity.WARNING
            assert args[3] == TEST_ALERT_TYPE_CUSTOM
            assert args[4] == details
            assert args[5] == TEST_USER_ID


class TestAlertDispatchMixinSendChartImage:
    """Tests for AlertDispatchMixin send_chart_image method."""

    @pytest.mark.asyncio
    async def test_send_chart_image_telegram_disabled(self) -> None:
        """Test send_chart_image returns False when telegram disabled."""

        class TestMixin(AlertDispatchMixin):
            telegram_enabled = False
            delivery_manager = None
            authorized_user_ids = None
            alert_throttle = None
            command_processor = None

        mixin = TestMixin()
        result = await mixin.send_chart_image(TEST_IMAGE_PATH, TEST_CAPTION)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_chart_image_with_target_user(self) -> None:
        """Test send_chart_image with target user."""

        class TestMixin(AlertDispatchMixin):
            telegram_enabled = True
            authorized_user_ids = [TEST_USER_ID, TEST_USER_ID_ALT]
            alert_throttle = None
            command_processor = None

        mixin = TestMixin()
        mixin.delivery_manager = MagicMock()
        mixin.delivery_manager.send_chart = AsyncMock(return_value=True)

        result = await mixin.send_chart_image(TEST_IMAGE_PATH, TEST_CAPTION, TEST_USER_ID)

        assert result is True
        mixin.delivery_manager.send_chart.assert_called_once_with(TEST_IMAGE_PATH, TEST_CAPTION, [TEST_USER_ID])

    @pytest.mark.asyncio
    async def test_send_chart_image_all_authorized_users(self) -> None:
        """Test send_chart_image sends to all authorized users."""

        class TestMixin(AlertDispatchMixin):
            telegram_enabled = True
            authorized_user_ids = [TEST_USER_ID, TEST_USER_ID_ALT]
            alert_throttle = None
            command_processor = None

        mixin = TestMixin()
        mixin.delivery_manager = MagicMock()
        mixin.delivery_manager.send_chart = AsyncMock(return_value=True)

        result = await mixin.send_chart_image(TEST_IMAGE_PATH, TEST_CAPTION)

        assert result is True
        mixin.delivery_manager.send_chart.assert_called_once_with(TEST_IMAGE_PATH, TEST_CAPTION, [TEST_USER_ID, TEST_USER_ID_ALT])

    @pytest.mark.asyncio
    async def test_send_chart_image_no_recipients(self) -> None:
        """Test send_chart_image returns False with no recipients."""

        class TestMixin(AlertDispatchMixin):
            telegram_enabled = True
            authorized_user_ids = []
            alert_throttle = None
            command_processor = None

        mixin = TestMixin()
        mixin.delivery_manager = MagicMock()

        result = await mixin.send_chart_image(TEST_IMAGE_PATH, TEST_CAPTION)

        assert result is False


class TestAlertDispatchMixinSendChart:
    """Tests for AlertDispatchMixin send_chart method."""

    @pytest.mark.asyncio
    async def test_send_chart_delegates_to_send_chart_image(self) -> None:
        """Test send_chart delegates to send_chart_image."""

        class TestMixin(AlertDispatchMixin):
            telegram_enabled = True
            authorized_user_ids = [TEST_USER_ID]
            alert_throttle = None
            command_processor = None

        mixin = TestMixin()
        mixin.delivery_manager = MagicMock()
        mixin.delivery_manager.send_chart = AsyncMock(return_value=True)

        result = await mixin.send_chart(TEST_IMAGE_PATH_ALT, TEST_CAPTION, TEST_USER_ID)

        assert result is True


class TestAlertDispatchMixinEnsureProc:
    """Tests for AlertDispatchMixin _ensure_proc method."""

    def test_ensure_proc_telegram_disabled(self) -> None:
        """Test _ensure_proc does nothing when telegram disabled."""

        class TestMixin(AlertDispatchMixin):
            telegram_enabled = False
            delivery_manager = None
            authorized_user_ids = None
            alert_throttle = None
            command_processor = None

        mixin = TestMixin()
        mixin._ensure_proc()

    @pytest.mark.asyncio
    async def test_ensure_proc_starts_command_processor(self) -> None:
        """Test _ensure_proc starts command processor."""

        class TestMixin(AlertDispatchMixin):
            telegram_enabled = True
            authorized_user_ids = None
            alert_throttle = None
            delivery_manager = None

        mixin = TestMixin()
        mixin.command_processor = MagicMock()
        mixin.command_processor.start = AsyncMock()

        mixin._ensure_proc()
        await asyncio.sleep(0.01)

    def test_ensure_proc_no_event_loop(self) -> None:
        """Test _ensure_proc handles no event loop."""

        class TestMixin(AlertDispatchMixin):
            telegram_enabled = True
            authorized_user_ids = None
            alert_throttle = None
            delivery_manager = None

        mixin = TestMixin()
        mixin.command_processor = MagicMock()

        mixin._ensure_proc()


class TestAlertDispatchMixinFlush:
    """Tests for AlertDispatchMixin _flush method."""

    @pytest.mark.asyncio
    async def test_flush_returns_none(self) -> None:
        """Test _flush returns None."""

        class TestMixin(AlertDispatchMixin):
            telegram_enabled = False
            delivery_manager = None
            authorized_user_ids = None
            alert_throttle = None
            command_processor = None

        mixin = TestMixin()
        result = await mixin._flush()

        assert result is None


class TestCommandHandlersMixinRegisterCmds:
    """Tests for CommandHandlersMixin _register_cmds method."""

    def test_register_cmds_registers_all_commands(self) -> None:
        """Test _register_cmds registers all command handlers."""

        class TestMixin(CommandHandlersMixin):
            telegram_enabled = True

        mixin = TestMixin()
        mixin.command_registry = MagicMock()
        mixin.command_coordinator = MagicMock()
        mixin.command_coordinator.handle_help = MagicMock()
        mixin.command_coordinator.handle_load = MagicMock()
        mixin.command_coordinator.handle_price = MagicMock()
        mixin.command_coordinator.handle_temp = MagicMock()
        mixin.command_coordinator.handle_pnl = MagicMock()

        with patch("common.telegram_surface_handler.TelegramSurfaceHandler") as mock_surface:
            mock_surface_instance = MagicMock()
            mock_surface.return_value = mock_surface_instance

            mixin._register_cmds()

            assert mixin.command_registry.register_command_handler.call_count == 5
            mixin.command_registry.register_command_handler.assert_any_call(TEST_COMMAND_HELP, mixin.command_coordinator.handle_help)
            mixin.command_registry.register_command_handler.assert_any_call(TEST_COMMAND_LOAD, mixin.command_coordinator.handle_load)
            mixin.command_registry.register_command_handler.assert_any_call(TEST_COMMAND_PRICE, mixin.command_coordinator.handle_price)
            mixin.command_registry.register_command_handler.assert_any_call(TEST_COMMAND_TEMP, mixin.command_coordinator.handle_temp)
            mixin.command_registry.register_command_handler.assert_any_call(TEST_COMMAND_PNL, mixin.command_coordinator.handle_pnl)
            mock_surface_instance.register_surface_command.assert_called_once()


class TestCommandHandlersMixinRegisterCommandHandler:
    """Tests for CommandHandlersMixin register_command_handler method."""

    def test_register_command_handler_telegram_enabled(self) -> None:
        """Test register_command_handler when telegram enabled."""

        class TestMixin(CommandHandlersMixin):
            telegram_enabled = True
            command_registry = None
            command_coordinator = None
            polling_coordinator = None
            command_processor = None

        mixin = TestMixin()
        mixin.command_registry = MagicMock()
        handler = MagicMock()

        mixin.register_command_handler(TEST_COMMAND_CUSTOM, handler)

        mixin.command_registry.register_command_handler.assert_called_once_with(TEST_COMMAND_CUSTOM, handler)

    def test_register_command_handler_telegram_disabled(self) -> None:
        """Test register_command_handler when telegram disabled."""

        class TestMixin(CommandHandlersMixin):
            telegram_enabled = False
            command_registry = None
            command_coordinator = None
            polling_coordinator = None
            command_processor = None

        mixin = TestMixin()
        handler = MagicMock()

        mixin.register_command_handler(TEST_COMMAND_CUSTOM, handler)


class TestCommandHandlersMixinPollTelegramUpdates:
    """Tests for CommandHandlersMixin poll_telegram_updates method."""

    @pytest.mark.asyncio
    async def test_poll_telegram_updates_telegram_enabled(self) -> None:
        """Test poll_telegram_updates when telegram enabled."""

        class TestMixin(CommandHandlersMixin):
            telegram_enabled = True
            command_registry = None
            command_coordinator = None
            command_processor = None

        mixin = TestMixin()
        mixin.polling_coordinator = MagicMock()
        mixin.polling_coordinator.poll_updates = AsyncMock()

        await mixin.poll_telegram_updates()

        mixin.polling_coordinator.poll_updates.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_telegram_updates_telegram_disabled(self) -> None:
        """Test poll_telegram_updates when telegram disabled."""

        class TestMixin(CommandHandlersMixin):
            telegram_enabled = False
            command_registry = None
            command_coordinator = None
            polling_coordinator = None
            command_processor = None

        mixin = TestMixin()

        await mixin.poll_telegram_updates()


class TestCommandHandlersMixinCommandQueue:
    """Tests for CommandHandlersMixin command_queue property."""

    def test_command_queue_telegram_disabled(self) -> None:
        """Test command_queue returns None when telegram disabled."""

        class TestMixin(CommandHandlersMixin):
            telegram_enabled = False
            command_registry = None
            command_coordinator = None
            polling_coordinator = None
            command_processor = None

        mixin = TestMixin()
        result = mixin.command_queue

        assert result is None

    def test_command_queue_telegram_enabled(self) -> None:
        """Test command_queue returns queue when telegram enabled."""

        class TestMixin(CommandHandlersMixin):
            telegram_enabled = True
            command_registry = None
            command_coordinator = None
            polling_coordinator = None

        mixin = TestMixin()
        mock_queue = MagicMock()
        mixin.command_processor = MagicMock()
        mixin.command_processor.command_queue = mock_queue

        result = mixin.command_queue

        assert result is mock_queue


class TestCommandHandlersMixinLastUpdateId:
    """Tests for CommandHandlersMixin last_update_id property."""

    def test_last_update_id_telegram_disabled(self) -> None:
        """Test last_update_id returns None when telegram disabled."""

        class TestMixin(CommandHandlersMixin):
            telegram_enabled = False
            command_registry = None
            command_coordinator = None
            polling_coordinator = None
            command_processor = None

        mixin = TestMixin()
        result = mixin.last_update_id

        assert result is None

    def test_last_update_id_telegram_enabled(self) -> None:
        """Test last_update_id returns update ID when telegram enabled."""

        class TestMixin(CommandHandlersMixin):
            telegram_enabled = True
            command_registry = None
            command_coordinator = None
            command_processor = None

        mixin = TestMixin()
        mixin.polling_coordinator = MagicMock()
        mixin.polling_coordinator.update_processor = MagicMock()
        mixin.polling_coordinator.update_processor.last_update_id = 42

        result = mixin.last_update_id

        assert result == 42


class TestCommandHandlersMixinQueueProcessorTask:
    """Tests for CommandHandlersMixin queue_processor_task property."""

    def test_queue_processor_task_telegram_disabled(self) -> None:
        """Test queue_processor_task returns None when telegram disabled."""

        class TestMixin(CommandHandlersMixin):
            telegram_enabled = False
            command_registry = None
            command_coordinator = None
            polling_coordinator = None
            command_processor = None

        mixin = TestMixin()
        result = mixin.queue_processor_task

        assert result is None

    def test_queue_processor_task_telegram_enabled(self) -> None:
        """Test queue_processor_task returns task when telegram enabled."""

        class TestMixin(CommandHandlersMixin):
            telegram_enabled = True
            command_registry = None
            command_coordinator = None
            polling_coordinator = None

        mixin = TestMixin()
        mock_task = MagicMock()
        mixin.command_processor = MagicMock()
        mixin.command_processor.processor_task = mock_task

        result = mixin.queue_processor_task

        assert result is mock_task


class TestRateLimitMixinLast429Time:
    """Tests for RateLimitMixin _last_429_time property."""

    def test_last_429_time_telegram_disabled(self) -> None:
        """Test _last_429_time returns None when telegram disabled."""

        class TestMixin(RateLimitMixin):
            telegram_enabled = False
            rate_limit_handler = None

        mixin = TestMixin()
        result = mixin._last_429_time

        assert result is None

    def test_last_429_time_no_handler(self) -> None:
        """Test _last_429_time returns None when handler is None."""

        class TestMixin(RateLimitMixin):
            telegram_enabled = True
            rate_limit_handler = None

        mixin = TestMixin()
        result = mixin._last_429_time

        assert result is None

    def test_last_429_time_with_handler(self) -> None:
        """Test _last_429_time returns time when handler exists."""

        class TestMixin(RateLimitMixin):
            telegram_enabled = True

        mixin = TestMixin()
        mixin.rate_limit_handler = MagicMock()
        mixin.rate_limit_handler._last_429_time = TEST_TIMESTAMP

        result = mixin._last_429_time

        assert result == TEST_TIMESTAMP


class TestRateLimitMixinLast429BackoffSeconds:
    """Tests for RateLimitMixin _last_429_backoff_seconds property."""

    def test_last_429_backoff_seconds_telegram_disabled(self) -> None:
        """Test _last_429_backoff_seconds returns None when telegram disabled."""

        class TestMixin(RateLimitMixin):
            telegram_enabled = False
            rate_limit_handler = None

        mixin = TestMixin()
        result = mixin._last_429_backoff_seconds

        assert result is None

    def test_last_429_backoff_seconds_no_handler(self) -> None:
        """Test _last_429_backoff_seconds returns None when handler is None."""

        class TestMixin(RateLimitMixin):
            telegram_enabled = True
            rate_limit_handler = None

        mixin = TestMixin()
        result = mixin._last_429_backoff_seconds

        assert result is None

    def test_last_429_backoff_seconds_with_handler(self) -> None:
        """Test _last_429_backoff_seconds returns seconds when handler exists."""

        class TestMixin(RateLimitMixin):
            telegram_enabled = True

        mixin = TestMixin()
        mixin.rate_limit_handler = MagicMock()
        mixin.rate_limit_handler._last_429_backoff_seconds = TEST_BACKOFF_SECONDS

        result = mixin._last_429_backoff_seconds

        assert result == TEST_BACKOFF_SECONDS


class TestRateLimitMixin429Count:
    """Tests for RateLimitMixin _429_count property."""

    def test_429_count_telegram_disabled(self) -> None:
        """Test _429_count returns None when telegram disabled."""

        class TestMixin(RateLimitMixin):
            telegram_enabled = False
            rate_limit_handler = None

        mixin = TestMixin()
        result = mixin._429_count

        assert result is None

    def test_429_count_no_handler(self) -> None:
        """Test _429_count returns None when handler is None."""

        class TestMixin(RateLimitMixin):
            telegram_enabled = True
            rate_limit_handler = None

        mixin = TestMixin()
        result = mixin._429_count

        assert result is None

    def test_429_count_with_handler(self) -> None:
        """Test _429_count returns count when handler exists."""

        class TestMixin(RateLimitMixin):
            telegram_enabled = True

        mixin = TestMixin()
        mixin.rate_limit_handler = MagicMock()
        mixin.rate_limit_handler._429_count = TEST_429_COUNT

        result = mixin._429_count

        assert result == TEST_429_COUNT


class TestPriceValidationMixinSetMetricsRecorder:
    """Tests for PriceValidationMixin set_metrics_recorder method."""

    def test_set_metrics_recorder(self) -> None:
        """Test set_metrics_recorder delegates to chart manager."""

        class TestMixin(PriceValidationMixin):
            pass

        mixin = TestMixin()
        mixin.chart_manager = MagicMock()
        recorder = MagicMock()

        mixin.set_metrics_recorder(recorder)

        mixin.chart_manager.set_metrics_recorder.assert_called_once_with(recorder)


class TestPriceValidationMixinShouldSendPriceValidationAlert:
    """Tests for PriceValidationMixin should_send_price_validation_alert method."""

    def test_should_send_price_validation_alert(self) -> None:
        """Test should_send_price_validation_alert delegates to tracker."""

        class TestMixin(PriceValidationMixin):
            pass

        mixin = TestMixin()
        mixin.price_tracker = MagicMock()
        mixin.price_tracker.should_send_alert.return_value = True
        details = {"key": "value"}

        result = mixin.should_send_price_validation_alert(TEST_CURRENCY_BTC, details)

        assert result is True
        mixin.price_tracker.should_send_alert.assert_called_once_with(TEST_CURRENCY_BTC, details)


class TestPriceValidationMixinClearPriceValidationAlert:
    """Tests for PriceValidationMixin clear_price_validation_alert method."""

    def test_clear_price_validation_alert(self) -> None:
        """Test clear_price_validation_alert delegates to tracker."""

        class TestMixin(PriceValidationMixin):
            pass

        mixin = TestMixin()
        mixin.price_tracker = MagicMock()
        mixin.price_tracker.clear_alert.return_value = True

        result = mixin.clear_price_validation_alert(TEST_CURRENCY_ETH)

        assert result is True
        mixin.price_tracker.clear_alert.assert_called_once_with(TEST_CURRENCY_ETH)


class TestPriceValidationMixinIsPriceValidationAlertActive:
    """Tests for PriceValidationMixin is_price_validation_alert_active method."""

    def test_is_price_validation_alert_active(self) -> None:
        """Test is_price_validation_alert_active delegates to tracker."""

        class TestMixin(PriceValidationMixin):
            pass

        mixin = TestMixin()
        mixin.price_tracker = MagicMock()
        mixin.price_tracker.is_alert_active.return_value = False

        result = mixin.is_price_validation_alert_active(TEST_CURRENCY_BTC)

        assert result is False
        mixin.price_tracker.is_alert_active.assert_called_once_with(TEST_CURRENCY_BTC)


class TestAlerterInit:
    """Tests for Alerter __init__ method."""

    def test_init_with_settings(self) -> None:
        """Test initialization with settings."""
        mock_settings = MagicMock()
        mock_settings.alerting.throttle_window_seconds = TEST_THROTTLE_WINDOW
        mock_settings.alerting.max_alerts_per_window = TEST_MAX_ALERTS

        with patch("common.alerter_helpers.alerter_components_builder.AlerterComponentsBuilder") as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder_class.return_value = mock_builder
            mock_builder.build.return_value = {
                "telegram_enabled": False,
                "authorized_user_ids": [],
                "alert_throttle": MagicMock(),
                "price_validation_tracker": MagicMock(),
            }

            with patch("common.alerter_helpers.chart_manager.ChartManager") as mock_chart:
                with patch("common.alerter_helpers.command_coordinator.CommandCoordinator") as mock_coord:
                    alerter = Alerter(mock_settings)

                    assert alerter.settings is mock_settings
                    assert alerter.rate_limit_handler is None
                    assert alerter.delivery_manager is None
                    assert alerter.command_registry is None
                    assert alerter.command_processor is None
                    assert alerter.polling_coordinator is None
                    assert alerter.alert_sender is None

    def test_init_without_settings_gets_default(self) -> None:
        """Test initialization without settings gets default from shared config."""
        mock_settings = MagicMock()
        mock_settings.alerting.throttle_window_seconds = TEST_THROTTLE_WINDOW
        mock_settings.alerting.max_alerts_per_window = TEST_MAX_ALERTS

        with patch("common.alerter_helpers.alerter_components_builder.AlerterComponentsBuilder") as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder_class.return_value = mock_builder
            mock_builder.build.return_value = {
                "telegram_enabled": False,
                "authorized_user_ids": [],
                "alert_throttle": MagicMock(),
                "price_validation_tracker": MagicMock(),
            }

            with patch("common.alerter_helpers.chart_manager.ChartManager"):
                with patch("common.alerter_helpers.command_coordinator.CommandCoordinator"):
                    with patch("common.config.shared.get_alerter_settings", return_value=mock_settings):
                        alerter = Alerter(None)

                        assert alerter.settings is mock_settings

    def test_init_telegram_enabled(self) -> None:
        """Test initialization with telegram enabled."""
        mock_settings = MagicMock()
        mock_settings.alerting.throttle_window_seconds = TEST_THROTTLE_WINDOW
        mock_settings.alerting.max_alerts_per_window = TEST_MAX_ALERTS

        with patch("common.alerter_helpers.alerter_components_builder.AlerterComponentsBuilder") as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder_class.return_value = mock_builder
            mock_delivery = MagicMock()
            mock_registry = MagicMock()
            mock_processor = MagicMock()
            mock_polling = MagicMock()
            mock_rate_limit = MagicMock()
            mock_suppression = MagicMock()
            mock_throttle = MagicMock()
            mock_tracker = MagicMock()

            mock_builder.build.return_value = {
                "telegram_enabled": True,
                "authorized_user_ids": [TEST_USER_ID],
                "alert_throttle": mock_throttle,
                "price_validation_tracker": mock_tracker,
                "delivery_manager": mock_delivery,
                "command_registry": mock_registry,
                "command_processor": mock_processor,
                "polling_coordinator": mock_polling,
                "rate_limit_handler": mock_rate_limit,
                "suppression_manager": mock_suppression,
            }

            with patch("common.alerter_helpers.chart_manager.ChartManager") as mock_chart:
                with patch("common.alerter_helpers.command_coordinator.CommandCoordinator") as mock_coord:
                    with patch("common.alerter_helpers.alert_sender.AlertSender") as mock_sender:
                        alerter = Alerter(mock_settings)

                        assert alerter.telegram_enabled is True
                        assert alerter.authorized_user_ids == [TEST_USER_ID]
                        assert alerter.delivery_manager is mock_delivery
                        assert alerter.command_registry is mock_registry
                        assert alerter.command_processor is mock_processor
                        assert alerter.polling_coordinator is mock_polling
                        assert alerter.rate_limit_handler is mock_rate_limit

    def test_init_registers_commands_when_telegram_enabled(self) -> None:
        """Test initialization registers commands when telegram enabled."""
        mock_settings = MagicMock()
        mock_settings.alerting.throttle_window_seconds = TEST_THROTTLE_WINDOW
        mock_settings.alerting.max_alerts_per_window = TEST_MAX_ALERTS

        with patch("common.alerter_helpers.alerter_components_builder.AlerterComponentsBuilder") as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder_class.return_value = mock_builder
            mock_registry = MagicMock()

            mock_builder.build.return_value = {
                "telegram_enabled": True,
                "authorized_user_ids": [TEST_USER_ID],
                "alert_throttle": MagicMock(),
                "price_validation_tracker": MagicMock(),
                "delivery_manager": MagicMock(),
                "command_registry": mock_registry,
                "command_processor": MagicMock(),
                "polling_coordinator": MagicMock(),
                "rate_limit_handler": MagicMock(),
                "suppression_manager": MagicMock(),
            }

            with patch("common.alerter_helpers.chart_manager.ChartManager"):
                with patch("common.alerter_helpers.command_coordinator.CommandCoordinator"):
                    with patch("common.alerter_helpers.alert_sender.AlertSender"):
                        with patch("common.telegram_surface_handler.TelegramSurfaceHandler") as mock_surface:
                            mock_surface_instance = MagicMock()
                            mock_surface.return_value = mock_surface_instance

                            alerter = Alerter(mock_settings)

                            assert mock_registry.register_command_handler.call_count >= 5


class TestAlerterCleanup:
    """Tests for Alerter cleanup method."""

    @pytest.mark.asyncio
    async def test_cleanup_telegram_disabled(self) -> None:
        """Test cleanup when telegram disabled."""
        mock_settings = MagicMock()
        mock_settings.alerting.throttle_window_seconds = TEST_THROTTLE_WINDOW
        mock_settings.alerting.max_alerts_per_window = TEST_MAX_ALERTS

        with patch("common.alerter_helpers.alerter_components_builder.AlerterComponentsBuilder") as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder_class.return_value = mock_builder
            mock_builder.build.return_value = {
                "telegram_enabled": False,
                "authorized_user_ids": [],
                "alert_throttle": MagicMock(),
                "price_validation_tracker": MagicMock(),
            }

            with patch("common.alerter_helpers.chart_manager.ChartManager"):
                with patch("common.alerter_helpers.command_coordinator.CommandCoordinator"):
                    alerter = Alerter(mock_settings)
                    await alerter.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_telegram_enabled(self) -> None:
        """Test cleanup stops command processor when telegram enabled."""
        mock_settings = MagicMock()
        mock_settings.alerting.throttle_window_seconds = TEST_THROTTLE_WINDOW
        mock_settings.alerting.max_alerts_per_window = TEST_MAX_ALERTS

        with patch("common.alerter_helpers.alerter_components_builder.AlerterComponentsBuilder") as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder_class.return_value = mock_builder
            mock_processor = MagicMock()
            mock_processor.stop = AsyncMock()

            mock_builder.build.return_value = {
                "telegram_enabled": True,
                "authorized_user_ids": [TEST_USER_ID],
                "alert_throttle": MagicMock(),
                "price_validation_tracker": MagicMock(),
                "delivery_manager": MagicMock(),
                "command_registry": MagicMock(),
                "command_processor": mock_processor,
                "polling_coordinator": MagicMock(),
                "rate_limit_handler": MagicMock(),
                "suppression_manager": MagicMock(),
            }

            with patch("common.alerter_helpers.chart_manager.ChartManager"):
                with patch("common.alerter_helpers.command_coordinator.CommandCoordinator"):
                    with patch("common.alerter_helpers.alert_sender.AlertSender"):
                        with patch("common.telegram_surface_handler.TelegramSurfaceHandler"):
                            alerter = Alerter(mock_settings)
                            await alerter.cleanup()

                            mock_processor.stop.assert_called_once()


class TestSendAlertFunction:
    """Tests for _send_alert function."""

    @pytest.mark.asyncio
    async def test_send_alert_telegram_enabled(self) -> None:
        """Test _send_alert with telegram enabled."""
        mock_alerter = MagicMock()
        mock_alerter.telegram_enabled = True
        mock_sender = MagicMock()
        mock_sender.send_alert = AsyncMock(return_value=True)
        mock_alerter.alert_sender = mock_sender

        result = await _send_alert(
            mock_alerter,
            TEST_MESSAGE,
            AlertSeverity.INFO,
            TEST_ALERT_TYPE_GENERAL,
            None,
            None,
        )

        assert result is True
        mock_sender.send_alert.assert_called_once_with(
            TEST_MESSAGE,
            AlertSeverity.INFO,
            TEST_ALERT_TYPE_GENERAL,
            None,
            None,
        )

    @pytest.mark.asyncio
    async def test_send_alert_telegram_disabled_throttled(self) -> None:
        """Test _send_alert with telegram disabled and throttled."""
        mock_alerter = MagicMock()
        mock_alerter.telegram_enabled = False
        mock_throttle = MagicMock()
        mock_throttle.record.return_value = False
        mock_alerter.alert_throttle = mock_throttle

        result = await _send_alert(
            mock_alerter,
            TEST_MESSAGE,
            AlertSeverity.WARNING,
            TEST_ALERT_TYPE_CUSTOM,
            None,
            None,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_telegram_disabled_allowed(self) -> None:
        """Test _send_alert with telegram disabled and allowed."""
        mock_alerter = MagicMock()
        mock_alerter.telegram_enabled = False
        mock_throttle = MagicMock()
        mock_throttle.record.return_value = True
        mock_alerter.alert_throttle = mock_throttle

        with patch("common.alerter.time.time", return_value=TEST_TIMESTAMP):
            result = await _send_alert(
                mock_alerter,
                TEST_MESSAGE_CRITICAL,
                AlertSeverity.CRITICAL,
                TEST_ALERT_TYPE_CUSTOM,
                {"detail": "value"},
                TEST_USER_ID,
            )

        assert result is True
        mock_throttle.record.assert_called_once()
        call_args = mock_throttle.record.call_args[0][0]
        assert call_args.message == TEST_MESSAGE_CRITICAL
        assert call_args.severity == AlertSeverity.CRITICAL
        assert call_args.timestamp == TEST_TIMESTAMP
        assert call_args.alert_type == TEST_ALERT_TYPE_CUSTOM
        assert call_args.details == {"detail": "value"}


class TestConstants:
    """Tests for module constants."""

    def test_alert_failure_errors(self) -> None:
        """Test ALERT_FAILURE_ERRORS contains expected error types."""
        import aiohttp

        assert aiohttp.ClientError in ALERT_FAILURE_ERRORS
        assert asyncio.TimeoutError in ALERT_FAILURE_ERRORS
        assert OSError in ALERT_FAILURE_ERRORS
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
        assert "PendingTelegramMedia" in alerter.__all__
        assert "PendingTelegramMessage" in alerter.__all__
        assert "QueuedCommand" in alerter.__all__
        assert "TelegramDeliveryResult" in alerter.__all__
