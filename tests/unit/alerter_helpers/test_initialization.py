"""Tests for initialization module."""

from unittest.mock import MagicMock, patch

import pytest

from common.alerter_helpers.initialization import AlerterInitializer

# Test constants for alerter configuration
TEST_TELEGRAM_TIMEOUT_SECONDS = 30
TEST_TELEGRAM_TIMEOUT_SECONDS_LONG = 100
TEST_TELEGRAM_TIMEOUT_SECONDS_SHORT = 5
TEST_THROTTLE_WINDOW_SECONDS = 60
TEST_MAX_ALERTS_PER_WINDOW = 10


@pytest.fixture
def mock_settings_with_telegram() -> MagicMock:
    """Create mock settings with Telegram enabled."""
    settings = MagicMock()
    settings.telegram.bot_token = "test_token_123"
    settings.telegram.chat_ids = [123, 456]
    settings.alerting.telegram_timeout_seconds = TEST_TELEGRAM_TIMEOUT_SECONDS
    settings.alerting.throttle_window_seconds = TEST_THROTTLE_WINDOW_SECONDS
    settings.alerting.max_alerts_per_window = TEST_MAX_ALERTS_PER_WINDOW
    return settings


@pytest.fixture
def mock_settings_without_telegram() -> MagicMock:
    """Create mock settings without Telegram."""
    settings = MagicMock()
    settings.telegram = None
    settings.alerting.throttle_window_seconds = TEST_THROTTLE_WINDOW_SECONDS
    settings.alerting.max_alerts_per_window = TEST_MAX_ALERTS_PER_WINDOW
    return settings


class TestAlerterInitializer:
    """Tests for AlerterInitializer class."""

    def test_init(self, mock_settings_with_telegram: MagicMock) -> None:
        """Test AlerterInitializer initialization."""
        initializer = AlerterInitializer(mock_settings_with_telegram)
        assert initializer.settings is mock_settings_with_telegram

    @patch("common.alerter_helpers.initialization.TelegramClient")
    @patch("common.alerter_helpers.initialization.AlertThrottle")
    @patch("common.alerter_helpers.initialization.AlertFormatter")
    @patch("common.alerter_helpers.initialization.AlertSuppressionManager")
    @patch("common.alerter_helpers.initialization.PriceValidationTracker")
    def test_initialize_with_telegram_enabled(
        self,
        mock_tracker: MagicMock,
        mock_suppression: MagicMock,
        mock_formatter: MagicMock,
        mock_throttle: MagicMock,
        mock_telegram_client: MagicMock,
        mock_settings_with_telegram: MagicMock,
    ) -> None:
        """Test initialization with Telegram enabled."""
        initializer = AlerterInitializer(mock_settings_with_telegram)

        with patch.object(initializer, "_initialize_telegram_helpers") as mock_init_helpers:
            result = initializer.initialize()

        assert result["telegram_enabled"] is True
        assert result["telegram_token"] == "test_token_123"
        assert result["authorized_user_ids"] == [123, 456]
        assert result["telegram_timeout_seconds"] == 30
        assert result["telegram_long_poll_timeout_seconds"] == 60
        mock_telegram_client.assert_called_once_with("test_token_123", timeout_seconds=30)
        mock_init_helpers.assert_called_once_with(result)

    @patch("common.alerter_helpers.initialization.AlertThrottle")
    @patch("common.alerter_helpers.initialization.AlertFormatter")
    @patch("common.alerter_helpers.initialization.AlertSuppressionManager")
    @patch("common.alerter_helpers.initialization.PriceValidationTracker")
    def test_initialize_without_telegram(
        self,
        mock_tracker: MagicMock,
        mock_suppression: MagicMock,
        mock_formatter: MagicMock,
        mock_throttle: MagicMock,
        mock_settings_without_telegram: MagicMock,
    ) -> None:
        """Test initialization with Telegram disabled."""
        initializer = AlerterInitializer(mock_settings_without_telegram)
        result = initializer.initialize()

        assert result["telegram_enabled"] is False
        assert result["telegram_token"] is None
        assert result["authorized_user_ids"] == []
        assert result["telegram_timeout_seconds"] == 0
        assert result["telegram_long_poll_timeout_seconds"] == 0
        assert result["telegram_client"] is None

    @patch("common.alerter_helpers.initialization.TelegramClient")
    @patch("common.alerter_helpers.initialization.AlertThrottle")
    @patch("common.alerter_helpers.initialization.AlertFormatter")
    @patch("common.alerter_helpers.initialization.AlertSuppressionManager")
    @patch("common.alerter_helpers.initialization.PriceValidationTracker")
    def test_initialize_creates_core_helpers(
        self,
        mock_tracker: MagicMock,
        mock_suppression: MagicMock,
        mock_formatter: MagicMock,
        mock_throttle: MagicMock,
        mock_telegram_client: MagicMock,
        mock_settings_without_telegram: MagicMock,
    ) -> None:
        """Test that core helpers are created."""
        initializer = AlerterInitializer(mock_settings_without_telegram)
        result = initializer.initialize()

        mock_formatter.assert_called_once()
        mock_suppression.assert_called_once()
        mock_tracker.assert_called_once()
        mock_throttle.assert_called_once_with(60, 10)
        assert "alert_formatter" in result
        assert "suppression_manager" in result
        assert "price_validation_tracker" in result
        assert "alert_throttle" in result

    def test_initialize_telegram_helpers(self) -> None:
        """Test _initialize_telegram_helpers creates all components."""
        with (
            patch("common.alerter_helpers.initialization.TelegramNetworkBackoffManager") as mock_backoff,
            patch("common.alerter_helpers.initialization.TelegramMessageSender") as mock_msg_sender,
            patch("common.alerter_helpers.initialization.TelegramMediaSender") as mock_media_sender,
            patch("common.alerter_helpers.initialization.TelegramDeliveryManager") as mock_delivery,
            patch("common.alerter_helpers.initialization.TelegramRateLimitHandler") as mock_rate_limit,
            patch("common.alerter_helpers.initialization.CommandAuthorizationChecker") as mock_auth_checker,
            patch("common.alerter_helpers.initialization.CommandHandlerRegistry") as mock_registry,
            patch("common.alerter_helpers.initialization.asyncio") as mock_asyncio,
        ):
            settings = MagicMock()
            initializer = AlerterInitializer(settings)

            result = {
                "telegram_client": MagicMock(),
                "telegram_timeout_seconds": 30,
                "alert_formatter": MagicMock(),
                "authorized_user_ids": [123],
            }

            initializer._initialize_telegram_helpers(result)

            mock_backoff.assert_called_once_with(30)
            mock_msg_sender.assert_called_once()
            mock_media_sender.assert_called_once()
            mock_delivery.assert_called_once()
            mock_rate_limit.assert_called_once()
            mock_auth_checker.assert_called_once_with([123])
            mock_registry.assert_called_once()
            mock_asyncio.Queue.assert_called_once()
            assert result["command_processor"] is None
            assert result["update_processor"] is None
            assert result["polling_executor"] is None
            assert result["polling_coordinator"] is None

    @patch("common.alerter_helpers.initialization.TelegramClient")
    @patch("common.alerter_helpers.initialization.AlertThrottle")
    @patch("common.alerter_helpers.initialization.AlertFormatter")
    @patch("common.alerter_helpers.initialization.AlertSuppressionManager")
    @patch("common.alerter_helpers.initialization.PriceValidationTracker")
    def test_telegram_long_poll_timeout_capped_at_60(
        self,
        mock_tracker: MagicMock,
        mock_suppression: MagicMock,
        mock_formatter: MagicMock,
        mock_throttle: MagicMock,
        mock_telegram_client: MagicMock,
        mock_settings_with_telegram: MagicMock,
    ) -> None:
        """Test that long poll timeout is capped at 60."""
        mock_settings_with_telegram.alerting.telegram_timeout_seconds = TEST_TELEGRAM_TIMEOUT_SECONDS_LONG
        initializer = AlerterInitializer(mock_settings_with_telegram)

        with patch.object(initializer, "_initialize_telegram_helpers"):
            result = initializer.initialize()

        assert result["telegram_long_poll_timeout_seconds"] == 60

    @patch("common.alerter_helpers.initialization.TelegramClient")
    @patch("common.alerter_helpers.initialization.AlertThrottle")
    @patch("common.alerter_helpers.initialization.AlertFormatter")
    @patch("common.alerter_helpers.initialization.AlertSuppressionManager")
    @patch("common.alerter_helpers.initialization.PriceValidationTracker")
    def test_telegram_long_poll_timeout_min_25(
        self,
        mock_tracker: MagicMock,
        mock_suppression: MagicMock,
        mock_formatter: MagicMock,
        mock_throttle: MagicMock,
        mock_telegram_client: MagicMock,
        mock_settings_with_telegram: MagicMock,
    ) -> None:
        """Test that long poll timeout has minimum of 25."""
        mock_settings_with_telegram.alerting.telegram_timeout_seconds = TEST_TELEGRAM_TIMEOUT_SECONDS_SHORT
        initializer = AlerterInitializer(mock_settings_with_telegram)

        with patch.object(initializer, "_initialize_telegram_helpers"):
            result = initializer.initialize()

        assert result["telegram_long_poll_timeout_seconds"] == 25
