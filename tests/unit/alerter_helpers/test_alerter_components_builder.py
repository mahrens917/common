"""Tests for alerter_helpers.alerter_components_builder module."""

from unittest.mock import MagicMock, patch

from common.alerter_helpers.alerter_components_builder import AlerterComponentsBuilder

# Test constants for alerter configuration
TEST_THROTTLE_WINDOW_SECONDS = 60
TEST_THROTTLE_WINDOW_SECONDS_CUSTOM = 120
TEST_THROTTLE_WINDOW_SECONDS_LONG = 300
TEST_MAX_ALERTS_PER_WINDOW = 5
TEST_MAX_ALERTS_PER_WINDOW_CUSTOM = 10
TEST_MAX_ALERTS_PER_WINDOW_LONG = 20


class TestAlerterComponentsBuilderInit:
    """Tests for AlerterComponentsBuilder initialization."""

    def test_stores_settings(self) -> None:
        """Test stores settings."""
        mock_settings = MagicMock()

        builder = AlerterComponentsBuilder(mock_settings)

        assert builder.settings is mock_settings

    def test_initializes_empty_result(self) -> None:
        """Test initializes empty result dict."""
        builder = AlerterComponentsBuilder(MagicMock())

        assert builder.result == {}


class TestAlerterComponentsBuilderBuild:
    """Tests for build method."""

    def test_returns_dict(self) -> None:
        """Test returns dictionary."""
        mock_settings = MagicMock()
        mock_settings.alerting.throttle_window_seconds = TEST_THROTTLE_WINDOW_SECONDS
        mock_settings.alerting.max_alerts_per_window = TEST_MAX_ALERTS_PER_WINDOW

        with patch("common.alerter_helpers.alerter_components_builder.TelegramBuilder") as mock_tg:
            mock_tg.build_telegram_config.return_value = {"telegram_enabled": False, "authorized_user_ids": set()}
            with patch("common.alerter_helpers.alerter_components_builder.AlertFormatter"):
                with patch("common.alerter_helpers.alerter_components_builder.AlertSuppressionManager"):
                    with patch("common.alerter_helpers.alerter_components_builder.PriceValidationTracker"):
                        with patch("common.alerter_helpers.alerter_components_builder.AlertThrottle"):
                            builder = AlerterComponentsBuilder(mock_settings)
                            result = builder.build(MagicMock(), MagicMock(), MagicMock())

                            assert isinstance(result, dict)

    def test_includes_telegram_config(self) -> None:
        """Test includes telegram configuration."""
        mock_settings = MagicMock()
        mock_settings.alerting.throttle_window_seconds = TEST_THROTTLE_WINDOW_SECONDS
        mock_settings.alerting.max_alerts_per_window = TEST_MAX_ALERTS_PER_WINDOW

        with patch("common.alerter_helpers.alerter_components_builder.TelegramBuilder") as mock_tg:
            mock_tg.build_telegram_config.return_value = {
                "telegram_enabled": True,
                "authorized_user_ids": {123},
            }
            mock_tg.build_basic_and_command_components.return_value = {}
            mock_tg.build_polling_components.return_value = {}
            with patch("common.alerter_helpers.alerter_components_builder.AlertFormatter"):
                with patch("common.alerter_helpers.alerter_components_builder.AlertSuppressionManager"):
                    with patch("common.alerter_helpers.alerter_components_builder.PriceValidationTracker"):
                        with patch("common.alerter_helpers.alerter_components_builder.AlertThrottle"):
                            builder = AlerterComponentsBuilder(mock_settings)
                            result = builder.build(MagicMock(), MagicMock(), MagicMock())

                            assert "telegram_enabled" in result
                            assert "authorized_user_ids" in result

    def test_includes_core_helpers(self) -> None:
        """Test includes core helper components."""
        mock_settings = MagicMock()
        mock_settings.alerting.throttle_window_seconds = TEST_THROTTLE_WINDOW_SECONDS
        mock_settings.alerting.max_alerts_per_window = TEST_MAX_ALERTS_PER_WINDOW

        mock_formatter = MagicMock()
        mock_suppression = MagicMock()
        mock_tracker = MagicMock()

        with patch("common.alerter_helpers.alerter_components_builder.TelegramBuilder") as mock_tg:
            mock_tg.build_telegram_config.return_value = {"telegram_enabled": False, "authorized_user_ids": set()}
            with patch("common.alerter_helpers.alerter_components_builder.AlertFormatter") as mock_fmt:
                mock_fmt.return_value = mock_formatter
                with patch("common.alerter_helpers.alerter_components_builder.AlertSuppressionManager") as mock_supp:
                    mock_supp.return_value = mock_suppression
                    with patch("common.alerter_helpers.alerter_components_builder.PriceValidationTracker") as mock_trk:
                        mock_trk.return_value = mock_tracker
                        with patch("common.alerter_helpers.alerter_components_builder.AlertThrottle"):
                            builder = AlerterComponentsBuilder(mock_settings)
                            result = builder.build(MagicMock(), MagicMock(), MagicMock())

                            assert result["alert_formatter"] is mock_formatter
                            assert result["suppression_manager"] is mock_suppression
                            assert result["price_validation_tracker"] is mock_tracker

    def test_includes_throttle(self) -> None:
        """Test includes alert throttle."""
        mock_settings = MagicMock()
        mock_settings.alerting.throttle_window_seconds = TEST_THROTTLE_WINDOW_SECONDS_CUSTOM
        mock_settings.alerting.max_alerts_per_window = TEST_MAX_ALERTS_PER_WINDOW_CUSTOM

        mock_throttle = MagicMock()

        with patch("common.alerter_helpers.alerter_components_builder.TelegramBuilder") as mock_tg:
            mock_tg.build_telegram_config.return_value = {"telegram_enabled": False, "authorized_user_ids": set()}
            with patch("common.alerter_helpers.alerter_components_builder.AlertFormatter"):
                with patch("common.alerter_helpers.alerter_components_builder.AlertSuppressionManager"):
                    with patch("common.alerter_helpers.alerter_components_builder.PriceValidationTracker"):
                        with patch("common.alerter_helpers.alerter_components_builder.AlertThrottle") as mock_th:
                            mock_th.return_value = mock_throttle
                            builder = AlerterComponentsBuilder(mock_settings)
                            result = builder.build(MagicMock(), MagicMock(), MagicMock())

                            mock_th.assert_called_once_with(TEST_THROTTLE_WINDOW_SECONDS_CUSTOM, TEST_MAX_ALERTS_PER_WINDOW_CUSTOM)
                            assert result["alert_throttle"] is mock_throttle

    def test_builds_telegram_components_when_enabled(self) -> None:
        """Test builds Telegram components when enabled."""
        mock_settings = MagicMock()
        mock_settings.alerting.throttle_window_seconds = TEST_THROTTLE_WINDOW_SECONDS
        mock_settings.alerting.max_alerts_per_window = TEST_MAX_ALERTS_PER_WINDOW

        with patch("common.alerter_helpers.alerter_components_builder.TelegramBuilder") as mock_tg:
            mock_tg.build_telegram_config.return_value = {
                "telegram_enabled": True,
                "authorized_user_ids": {123},
            }
            mock_tg.build_basic_and_command_components.return_value = {"delivery_manager": MagicMock()}
            mock_tg.build_polling_components.return_value = {"polling_coordinator": MagicMock()}
            with patch("common.alerter_helpers.alerter_components_builder.AlertFormatter"):
                with patch("common.alerter_helpers.alerter_components_builder.AlertSuppressionManager"):
                    with patch("common.alerter_helpers.alerter_components_builder.PriceValidationTracker"):
                        with patch("common.alerter_helpers.alerter_components_builder.AlertThrottle"):
                            builder = AlerterComponentsBuilder(mock_settings)
                            builder.build(MagicMock(), MagicMock(), MagicMock())

                            mock_tg.build_basic_and_command_components.assert_called_once()
                            mock_tg.build_polling_components.assert_called_once()

    def test_skips_telegram_components_when_disabled(self) -> None:
        """Test skips Telegram components when disabled."""
        mock_settings = MagicMock()
        mock_settings.alerting.throttle_window_seconds = TEST_THROTTLE_WINDOW_SECONDS
        mock_settings.alerting.max_alerts_per_window = TEST_MAX_ALERTS_PER_WINDOW

        with patch("common.alerter_helpers.alerter_components_builder.TelegramBuilder") as mock_tg:
            mock_tg.build_telegram_config.return_value = {
                "telegram_enabled": False,
                "authorized_user_ids": set(),
            }
            with patch("common.alerter_helpers.alerter_components_builder.AlertFormatter"):
                with patch("common.alerter_helpers.alerter_components_builder.AlertSuppressionManager"):
                    with patch("common.alerter_helpers.alerter_components_builder.PriceValidationTracker"):
                        with patch("common.alerter_helpers.alerter_components_builder.AlertThrottle"):
                            builder = AlerterComponentsBuilder(mock_settings)
                            builder.build(MagicMock(), MagicMock(), MagicMock())

                            mock_tg.build_basic_and_command_components.assert_not_called()
                            mock_tg.build_polling_components.assert_not_called()


class TestAlerterComponentsBuilderBuildCoreHelpers:
    """Tests for _build_core_helpers method."""

    def test_creates_alert_formatter(self) -> None:
        """Test creates AlertFormatter."""
        mock_formatter = MagicMock()

        with patch("common.alerter_helpers.alerter_components_builder.AlertFormatter") as mock_cls:
            mock_cls.return_value = mock_formatter
            with patch("common.alerter_helpers.alerter_components_builder.AlertSuppressionManager"):
                with patch("common.alerter_helpers.alerter_components_builder.PriceValidationTracker"):
                    builder = AlerterComponentsBuilder(MagicMock())
                    builder._build_core_helpers()

                    assert builder.result["alert_formatter"] is mock_formatter

    def test_creates_suppression_manager(self) -> None:
        """Test creates AlertSuppressionManager."""
        mock_manager = MagicMock()

        with patch("common.alerter_helpers.alerter_components_builder.AlertFormatter"):
            with patch("common.alerter_helpers.alerter_components_builder.AlertSuppressionManager") as mock_cls:
                mock_cls.return_value = mock_manager
                with patch("common.alerter_helpers.alerter_components_builder.PriceValidationTracker"):
                    builder = AlerterComponentsBuilder(MagicMock())
                    builder._build_core_helpers()

                    assert builder.result["suppression_manager"] is mock_manager


class TestAlerterComponentsBuilderBuildThrottle:
    """Tests for _build_throttle method."""

    def test_creates_throttle_with_settings(self) -> None:
        """Test creates throttle with settings values."""
        mock_settings = MagicMock()
        mock_settings.alerting.throttle_window_seconds = TEST_THROTTLE_WINDOW_SECONDS_LONG
        mock_settings.alerting.max_alerts_per_window = TEST_MAX_ALERTS_PER_WINDOW_LONG

        with patch("common.alerter_helpers.alerter_components_builder.AlertThrottle") as mock_cls:
            builder = AlerterComponentsBuilder(mock_settings)
            builder._build_throttle()

            mock_cls.assert_called_once_with(TEST_THROTTLE_WINDOW_SECONDS_LONG, TEST_MAX_ALERTS_PER_WINDOW_LONG)
            assert "alert_throttle" in builder.result
