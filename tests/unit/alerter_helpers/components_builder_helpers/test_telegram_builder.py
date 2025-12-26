"""Tests for telegram_builder module."""

import asyncio
from unittest.mock import MagicMock, patch

from common.alerter_helpers.components_builder_helpers.telegram_builder import TelegramBuilder

# Test constants for Telegram configuration
TEST_BOT_TOKEN = "test_bot_token_123456789"
TEST_CHAT_ID_1 = 123456789
TEST_CHAT_ID_2 = 987654321
TEST_TIMEOUT_SECONDS = 30
TEST_TIMEOUT_SECONDS_SHORT = 15
TEST_TIMEOUT_SECONDS_LONG = 45
TEST_LONG_POLL_TIMEOUT_MIN = 25
TEST_LONG_POLL_TIMEOUT_MAX = 60
TEST_LONG_POLL_TIMEOUT_CALCULATED = 60
TEST_LONG_POLL_TIMEOUT_CALCULATED_SHORT = 30
TEST_TIMEOUT_SECONDS_MIN_CAP_TRIGGER = 10


class TestBuildTelegramConfigEnabled:
    """Tests for build_telegram_config when Telegram is enabled."""

    def test_returns_dict_with_enabled_true(self) -> None:
        """Test returns dict with telegram_enabled=True when configured."""
        mock_settings = MagicMock()
        mock_settings.telegram.bot_token = TEST_BOT_TOKEN
        mock_settings.telegram.chat_ids = [TEST_CHAT_ID_1, TEST_CHAT_ID_2]
        mock_settings.alerting.telegram_timeout_seconds = TEST_TIMEOUT_SECONDS

        result = TelegramBuilder.build_telegram_config(mock_settings)

        assert result["telegram_enabled"] is True

    def test_includes_bot_token(self) -> None:
        """Test includes bot token from settings."""
        mock_settings = MagicMock()
        mock_settings.telegram.bot_token = TEST_BOT_TOKEN
        mock_settings.telegram.chat_ids = [TEST_CHAT_ID_1]
        mock_settings.alerting.telegram_timeout_seconds = TEST_TIMEOUT_SECONDS

        result = TelegramBuilder.build_telegram_config(mock_settings)

        assert result["telegram_token"] == TEST_BOT_TOKEN

    def test_converts_chat_ids_to_list(self) -> None:
        """Test converts chat IDs to list."""
        mock_settings = MagicMock()
        mock_settings.telegram.bot_token = TEST_BOT_TOKEN
        mock_settings.telegram.chat_ids = [TEST_CHAT_ID_1, TEST_CHAT_ID_2]
        mock_settings.alerting.telegram_timeout_seconds = TEST_TIMEOUT_SECONDS

        result = TelegramBuilder.build_telegram_config(mock_settings)

        assert result["authorized_user_ids"] == [TEST_CHAT_ID_1, TEST_CHAT_ID_2]

    def test_includes_timeout_seconds(self) -> None:
        """Test includes timeout seconds from settings."""
        mock_settings = MagicMock()
        mock_settings.telegram.bot_token = TEST_BOT_TOKEN
        mock_settings.telegram.chat_ids = [TEST_CHAT_ID_1]
        mock_settings.alerting.telegram_timeout_seconds = TEST_TIMEOUT_SECONDS

        result = TelegramBuilder.build_telegram_config(mock_settings)

        assert result["telegram_timeout_seconds"] == TEST_TIMEOUT_SECONDS

    def test_calculates_long_poll_timeout_max_cap(self) -> None:
        """Test long poll timeout is capped at 60 seconds."""
        mock_settings = MagicMock()
        mock_settings.telegram.bot_token = TEST_BOT_TOKEN
        mock_settings.telegram.chat_ids = [TEST_CHAT_ID_1]
        mock_settings.alerting.telegram_timeout_seconds = TEST_TIMEOUT_SECONDS_LONG

        result = TelegramBuilder.build_telegram_config(mock_settings)

        assert result["telegram_long_poll_timeout_seconds"] == TEST_LONG_POLL_TIMEOUT_MAX

    def test_calculates_long_poll_timeout_min_cap(self) -> None:
        """Test long poll timeout is minimum 25 seconds."""
        mock_settings = MagicMock()
        mock_settings.telegram.bot_token = TEST_BOT_TOKEN
        mock_settings.telegram.chat_ids = [TEST_CHAT_ID_1]
        mock_settings.alerting.telegram_timeout_seconds = TEST_TIMEOUT_SECONDS_MIN_CAP_TRIGGER

        result = TelegramBuilder.build_telegram_config(mock_settings)

        assert result["telegram_long_poll_timeout_seconds"] == TEST_LONG_POLL_TIMEOUT_MIN

    def test_calculates_long_poll_timeout_normal(self) -> None:
        """Test long poll timeout is calculated as timeout * 2."""
        mock_settings = MagicMock()
        mock_settings.telegram.bot_token = TEST_BOT_TOKEN
        mock_settings.telegram.chat_ids = [TEST_CHAT_ID_1]
        mock_settings.alerting.telegram_timeout_seconds = TEST_TIMEOUT_SECONDS

        result = TelegramBuilder.build_telegram_config(mock_settings)

        assert result["telegram_long_poll_timeout_seconds"] == TEST_LONG_POLL_TIMEOUT_CALCULATED

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramClient")
    def test_creates_telegram_client(self, mock_client_class) -> None:
        """Test creates TelegramClient with correct parameters."""
        mock_settings = MagicMock()
        mock_settings.telegram.bot_token = TEST_BOT_TOKEN
        mock_settings.telegram.chat_ids = [TEST_CHAT_ID_1]
        mock_settings.alerting.telegram_timeout_seconds = TEST_TIMEOUT_SECONDS

        result = TelegramBuilder.build_telegram_config(mock_settings)

        mock_client_class.assert_called_once_with(TEST_BOT_TOKEN, timeout_seconds=TEST_TIMEOUT_SECONDS)
        assert result["telegram_client"] is mock_client_class.return_value

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.logger")
    def test_logs_enabled_message(self, mock_logger) -> None:
        """Test logs message when Telegram is enabled."""
        mock_settings = MagicMock()
        mock_settings.telegram.bot_token = TEST_BOT_TOKEN
        mock_settings.telegram.chat_ids = [TEST_CHAT_ID_1, TEST_CHAT_ID_2]
        mock_settings.alerting.telegram_timeout_seconds = TEST_TIMEOUT_SECONDS

        TelegramBuilder.build_telegram_config(mock_settings)

        mock_logger.info.assert_called_once_with(
            "Telegram notifications enabled for %s authorized user(s)",
            2,
        )


class TestBuildTelegramConfigDisabled:
    """Tests for build_telegram_config when Telegram is disabled."""

    def test_returns_dict_with_enabled_false(self) -> None:
        """Test returns dict with telegram_enabled=False when not configured."""
        mock_settings = MagicMock()
        mock_settings.telegram = None

        result = TelegramBuilder.build_telegram_config(mock_settings)

        assert result["telegram_enabled"] is False

    def test_returns_none_for_token(self) -> None:
        """Test returns None for token when disabled."""
        mock_settings = MagicMock()
        mock_settings.telegram = None

        result = TelegramBuilder.build_telegram_config(mock_settings)

        assert result["telegram_token"] is None

    def test_returns_empty_list_for_user_ids(self) -> None:
        """Test returns empty list for authorized user IDs when disabled."""
        mock_settings = MagicMock()
        mock_settings.telegram = None

        result = TelegramBuilder.build_telegram_config(mock_settings)

        assert result["authorized_user_ids"] == []

    def test_returns_zero_for_timeout_seconds(self) -> None:
        """Test returns zero for timeout seconds when disabled."""
        mock_settings = MagicMock()
        mock_settings.telegram = None

        result = TelegramBuilder.build_telegram_config(mock_settings)

        assert result["telegram_timeout_seconds"] == 0

    def test_returns_zero_for_long_poll_timeout(self) -> None:
        """Test returns zero for long poll timeout when disabled."""
        mock_settings = MagicMock()
        mock_settings.telegram = None

        result = TelegramBuilder.build_telegram_config(mock_settings)

        assert result["telegram_long_poll_timeout_seconds"] == 0

    def test_returns_none_for_client(self) -> None:
        """Test returns None for telegram client when disabled."""
        mock_settings = MagicMock()
        mock_settings.telegram = None

        result = TelegramBuilder.build_telegram_config(mock_settings)

        assert result["telegram_client"] is None

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.logger")
    def test_logs_disabled_message(self, mock_logger) -> None:
        """Test logs message when Telegram is disabled."""
        mock_settings = MagicMock()
        mock_settings.telegram = None

        TelegramBuilder.build_telegram_config(mock_settings)

        mock_logger.info.assert_called_once_with("Telegram notifications disabled - configuration not provided")


class TestBuildBasicAndCommandComponents:
    """Tests for build_basic_and_command_components method."""

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramNetworkBackoffManager")
    def test_creates_backoff_manager(self, mock_backoff_class) -> None:
        """Test creates TelegramNetworkBackoffManager with timeout."""
        mock_result = {
            "telegram_timeout_seconds": TEST_TIMEOUT_SECONDS,
            "telegram_client": MagicMock(),
            "authorized_user_ids": [TEST_CHAT_ID_1],
            "alert_formatter": MagicMock(),
        }
        mock_callback = MagicMock()

        result = TelegramBuilder.build_basic_and_command_components(mock_result, mock_callback)

        mock_backoff_class.assert_called_once_with(TEST_TIMEOUT_SECONDS)
        assert result["backoff_manager"] is mock_backoff_class.return_value

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.asyncio.Queue")
    def test_creates_command_queue(self, mock_queue_class) -> None:
        """Test creates asyncio Queue for commands."""
        mock_result = {
            "telegram_timeout_seconds": TEST_TIMEOUT_SECONDS,
            "telegram_client": MagicMock(),
            "authorized_user_ids": [TEST_CHAT_ID_1],
            "alert_formatter": MagicMock(),
        }
        mock_callback = MagicMock()

        result = TelegramBuilder.build_basic_and_command_components(mock_result, mock_callback)

        mock_queue_class.assert_called_once()
        assert result["command_queue"] is mock_queue_class.return_value

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramMessageSender")
    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramNetworkBackoffManager")
    def test_creates_message_sender(self, mock_backoff_class, mock_sender_class) -> None:
        """Test creates TelegramMessageSender with client, timeout, and backoff manager."""
        mock_client = MagicMock()
        mock_result = {
            "telegram_timeout_seconds": TEST_TIMEOUT_SECONDS,
            "telegram_client": mock_client,
            "authorized_user_ids": [TEST_CHAT_ID_1],
            "alert_formatter": MagicMock(),
        }
        mock_callback = MagicMock()

        result = TelegramBuilder.build_basic_and_command_components(mock_result, mock_callback)

        mock_sender_class.assert_called_once_with(mock_client, TEST_TIMEOUT_SECONDS, mock_backoff_class.return_value)
        assert result["message_sender"] is mock_sender_class.return_value

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramMediaSender")
    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramNetworkBackoffManager")
    def test_creates_media_sender(self, mock_backoff_class, mock_media_class) -> None:
        """Test creates TelegramMediaSender with client, timeout, and backoff manager."""
        mock_client = MagicMock()
        mock_result = {
            "telegram_timeout_seconds": TEST_TIMEOUT_SECONDS,
            "telegram_client": mock_client,
            "authorized_user_ids": [TEST_CHAT_ID_1],
            "alert_formatter": MagicMock(),
        }
        mock_callback = MagicMock()

        result = TelegramBuilder.build_basic_and_command_components(mock_result, mock_callback)

        mock_media_class.assert_called_once_with(mock_client, TEST_TIMEOUT_SECONDS, mock_backoff_class.return_value)
        assert result["media_sender"] is mock_media_class.return_value

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.CommandAuthorizationChecker")
    def test_creates_authorization_checker(self, mock_auth_class) -> None:
        """Test creates CommandAuthorizationChecker with authorized user IDs."""
        mock_result = {
            "telegram_timeout_seconds": TEST_TIMEOUT_SECONDS,
            "telegram_client": MagicMock(),
            "authorized_user_ids": [TEST_CHAT_ID_1, TEST_CHAT_ID_2],
            "alert_formatter": MagicMock(),
        }
        mock_callback = MagicMock()

        result = TelegramBuilder.build_basic_and_command_components(mock_result, mock_callback)

        mock_auth_class.assert_called_once_with([TEST_CHAT_ID_1, TEST_CHAT_ID_2])
        assert result["authorization_checker"] is mock_auth_class.return_value

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.CommandHandlerRegistry")
    def test_creates_command_registry(self, mock_registry_class) -> None:
        """Test creates CommandHandlerRegistry."""
        mock_result = {
            "telegram_timeout_seconds": TEST_TIMEOUT_SECONDS,
            "telegram_client": MagicMock(),
            "authorized_user_ids": [TEST_CHAT_ID_1],
            "alert_formatter": MagicMock(),
        }
        mock_callback = MagicMock()

        result = TelegramBuilder.build_basic_and_command_components(mock_result, mock_callback)

        mock_registry_class.assert_called_once()
        assert result["command_registry"] is mock_registry_class.return_value

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramDeliveryManager")
    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramMessageSender")
    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramMediaSender")
    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramNetworkBackoffManager")
    def test_creates_delivery_manager(self, mock_backoff_class, mock_media_class, mock_msg_class, mock_delivery_class) -> None:
        """Test creates TelegramDeliveryManager with senders and formatter."""
        mock_formatter = MagicMock()
        mock_result = {
            "telegram_timeout_seconds": TEST_TIMEOUT_SECONDS,
            "telegram_client": MagicMock(),
            "authorized_user_ids": [TEST_CHAT_ID_1],
            "alert_formatter": mock_formatter,
        }
        mock_callback = MagicMock()

        result = TelegramBuilder.build_basic_and_command_components(mock_result, mock_callback)

        mock_delivery_class.assert_called_once_with(mock_msg_class.return_value, mock_media_class.return_value, mock_formatter)
        assert result["delivery_manager"] is mock_delivery_class.return_value

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramRateLimitHandler")
    def test_creates_rate_limit_handler(self, mock_rate_class) -> None:
        """Test creates TelegramRateLimitHandler."""
        mock_result = {
            "telegram_timeout_seconds": TEST_TIMEOUT_SECONDS,
            "telegram_client": MagicMock(),
            "authorized_user_ids": [TEST_CHAT_ID_1],
            "alert_formatter": MagicMock(),
        }
        mock_callback = MagicMock()

        result = TelegramBuilder.build_basic_and_command_components(mock_result, mock_callback)

        mock_rate_class.assert_called_once()
        assert result["rate_limit_handler"] is mock_rate_class.return_value

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.CommandQueueProcessor")
    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.asyncio.Queue")
    def test_creates_command_processor(self, mock_queue_class, mock_processor_class) -> None:
        """Test creates CommandQueueProcessor with queue and callback."""
        mock_result = {
            "telegram_timeout_seconds": TEST_TIMEOUT_SECONDS,
            "telegram_client": MagicMock(),
            "authorized_user_ids": [TEST_CHAT_ID_1],
            "alert_formatter": MagicMock(),
        }
        mock_callback = MagicMock()

        result = TelegramBuilder.build_basic_and_command_components(mock_result, mock_callback)

        mock_processor_class.assert_called_once_with(mock_queue_class.return_value, mock_callback)
        assert result["command_processor"] is mock_processor_class.return_value

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramUpdateProcessor")
    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.CommandAuthorizationChecker")
    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.CommandHandlerRegistry")
    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.asyncio.Queue")
    def test_creates_update_processor(self, mock_queue_class, mock_registry_class, mock_auth_class, mock_update_class) -> None:
        """Test creates TelegramUpdateProcessor with all dependencies."""
        mock_result = {
            "telegram_timeout_seconds": TEST_TIMEOUT_SECONDS,
            "telegram_client": MagicMock(),
            "authorized_user_ids": [TEST_CHAT_ID_1],
            "alert_formatter": MagicMock(),
        }
        mock_callback = MagicMock()

        result = TelegramBuilder.build_basic_and_command_components(mock_result, mock_callback)

        mock_update_class.assert_called_once_with(
            mock_auth_class.return_value,
            mock_registry_class.return_value,
            mock_queue_class.return_value,
            mock_callback,
        )
        assert result["update_processor"] is mock_update_class.return_value


class TestBuildPollingComponents:
    """Tests for build_polling_components method."""

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramPollingRequestExecutor")
    def test_creates_polling_executor(self, mock_executor_class) -> None:
        """Test creates TelegramPollingRequestExecutor with dependencies."""
        mock_rate_handler = MagicMock()
        mock_update_processor = MagicMock()
        mock_backoff_mgr = MagicMock()
        mock_result = {
            "telegram_timeout_seconds": TEST_TIMEOUT_SECONDS,
            "telegram_client": MagicMock(),
            "telegram_long_poll_timeout_seconds": TEST_LONG_POLL_TIMEOUT_CALCULATED,
            "rate_limit_handler": mock_rate_handler,
            "update_processor": mock_update_processor,
            "backoff_manager": mock_backoff_mgr,
        }
        mock_send_callback = MagicMock()
        mock_flush_callback = MagicMock()
        mock_ensure_callback = MagicMock()

        result = TelegramBuilder.build_polling_components(mock_result, mock_send_callback, mock_flush_callback, mock_ensure_callback)

        mock_executor_class.assert_called_once_with(
            mock_rate_handler,
            mock_update_processor,
            mock_backoff_mgr,
            mock_flush_callback,
        )
        assert result["polling_executor"] is mock_executor_class.return_value

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramCoordinatorConfig")
    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramPollingRequestExecutor")
    def test_creates_coordinator_config(self, mock_executor_class, mock_config_class) -> None:
        """Test creates TelegramCoordinatorConfig with client and timeouts."""
        mock_client = MagicMock()
        mock_result = {
            "telegram_timeout_seconds": TEST_TIMEOUT_SECONDS,
            "telegram_client": mock_client,
            "telegram_long_poll_timeout_seconds": TEST_LONG_POLL_TIMEOUT_CALCULATED,
            "rate_limit_handler": MagicMock(),
            "update_processor": MagicMock(),
            "backoff_manager": MagicMock(),
        }
        mock_send_callback = MagicMock()
        mock_flush_callback = MagicMock()
        mock_ensure_callback = MagicMock()

        TelegramBuilder.build_polling_components(mock_result, mock_send_callback, mock_flush_callback, mock_ensure_callback)

        mock_config_class.assert_called_once_with(
            telegram_client=mock_client,
            telegram_timeout_seconds=TEST_TIMEOUT_SECONDS,
            telegram_long_poll_timeout_seconds=TEST_LONG_POLL_TIMEOUT_CALCULATED,
        )

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramCoordinatorDependencies")
    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramPollingRequestExecutor")
    def test_creates_coordinator_dependencies(self, mock_executor_class, mock_deps_class) -> None:
        """Test creates TelegramCoordinatorDependencies with all components."""
        mock_rate_handler = MagicMock()
        mock_update_processor = MagicMock()
        mock_backoff_mgr = MagicMock()
        mock_result = {
            "telegram_timeout_seconds": TEST_TIMEOUT_SECONDS,
            "telegram_client": MagicMock(),
            "telegram_long_poll_timeout_seconds": TEST_LONG_POLL_TIMEOUT_CALCULATED,
            "rate_limit_handler": mock_rate_handler,
            "update_processor": mock_update_processor,
            "backoff_manager": mock_backoff_mgr,
        }
        mock_send_callback = MagicMock()
        mock_flush_callback = MagicMock()
        mock_ensure_callback = MagicMock()

        TelegramBuilder.build_polling_components(mock_result, mock_send_callback, mock_flush_callback, mock_ensure_callback)

        mock_deps_class.assert_called_once_with(
            rate_limit_handler=mock_rate_handler,
            request_executor=mock_executor_class.return_value,
            backoff_manager=mock_backoff_mgr,
            update_processor=mock_update_processor,
            queue_processor_starter=mock_ensure_callback,
        )

    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramPollingCoordinator")
    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramCoordinatorConfig")
    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramCoordinatorDependencies")
    @patch("common.alerter_helpers.components_builder_helpers.telegram_builder.TelegramPollingRequestExecutor")
    def test_creates_polling_coordinator(self, mock_executor_class, mock_deps_class, mock_config_class, mock_coordinator_class) -> None:
        """Test creates TelegramPollingCoordinator with config and dependencies."""
        mock_result = {
            "telegram_timeout_seconds": TEST_TIMEOUT_SECONDS,
            "telegram_client": MagicMock(),
            "telegram_long_poll_timeout_seconds": TEST_LONG_POLL_TIMEOUT_CALCULATED,
            "rate_limit_handler": MagicMock(),
            "update_processor": MagicMock(),
            "backoff_manager": MagicMock(),
        }
        mock_send_callback = MagicMock()
        mock_flush_callback = MagicMock()
        mock_ensure_callback = MagicMock()

        result = TelegramBuilder.build_polling_components(mock_result, mock_send_callback, mock_flush_callback, mock_ensure_callback)

        mock_coordinator_class.assert_called_once_with(
            config=mock_config_class.return_value,
            dependencies=mock_deps_class.return_value,
        )
        assert result["polling_coordinator"] is mock_coordinator_class.return_value
