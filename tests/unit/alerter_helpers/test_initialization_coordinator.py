"""Tests for alerter_helpers.initialization_coordinator module."""

from unittest.mock import MagicMock, patch

from common.alerter_helpers.initialization_coordinator import InitializationCoordinator


class TestInitializationCoordinatorInitializeComponents:
    """Tests for initialize_components static method."""

    def test_returns_dict(self) -> None:
        """Test returns dictionary."""
        mock_settings = MagicMock()
        mock_components = {
            "telegram_enabled": False,
            "authorized_user_ids": set(),
        }

        with patch("common.alerter_helpers.initialization_coordinator.AlerterComponentsBuilder") as mock_builder:
            mock_builder.return_value.build.return_value = mock_components

            result = InitializationCoordinator.initialize_components(
                settings=mock_settings,
                send_alert_callback=MagicMock(),
                flush_callback=MagicMock(),
                ensure_proc_callback=MagicMock(),
            )

            assert isinstance(result, dict)

    def test_includes_telegram_enabled(self) -> None:
        """Test includes telegram_enabled in result."""
        mock_settings = MagicMock()
        mock_components = {
            "telegram_enabled": True,
            "authorized_user_ids": {123},
            "delivery_manager": MagicMock(),
            "command_registry": MagicMock(),
            "command_processor": MagicMock(),
            "polling_coordinator": MagicMock(),
            "price_validation_tracker": MagicMock(),
            "suppression_manager": MagicMock(),
            "alert_throttle": MagicMock(),
        }

        with patch("common.alerter_helpers.initialization_coordinator.AlerterComponentsBuilder") as mock_builder:
            mock_builder.return_value.build.return_value = mock_components
            with patch("common.alerter_helpers.initialization_coordinator.AlertSender"):
                result = InitializationCoordinator.initialize_components(
                    settings=mock_settings,
                    send_alert_callback=MagicMock(),
                    flush_callback=MagicMock(),
                    ensure_proc_callback=MagicMock(),
                )

                assert "telegram_enabled" in result

    def test_includes_authorized_user_ids(self) -> None:
        """Test includes authorized_user_ids in result."""
        mock_settings = MagicMock()
        mock_components = {
            "telegram_enabled": False,
            "authorized_user_ids": {456, 789},
        }

        with patch("common.alerter_helpers.initialization_coordinator.AlerterComponentsBuilder") as mock_builder:
            mock_builder.return_value.build.return_value = mock_components

            result = InitializationCoordinator.initialize_components(
                settings=mock_settings,
                send_alert_callback=MagicMock(),
                flush_callback=MagicMock(),
                ensure_proc_callback=MagicMock(),
            )

            assert result["authorized_user_ids"] == {456, 789}

    def test_includes_telegram_components_when_enabled(self) -> None:
        """Test includes telegram components when enabled."""
        mock_settings = MagicMock()
        mock_delivery_manager = MagicMock()
        mock_command_registry = MagicMock()
        mock_components = {
            "telegram_enabled": True,
            "authorized_user_ids": {123},
            "delivery_manager": mock_delivery_manager,
            "command_registry": mock_command_registry,
            "command_processor": MagicMock(),
            "polling_coordinator": MagicMock(),
            "price_validation_tracker": MagicMock(),
            "suppression_manager": MagicMock(),
            "alert_throttle": MagicMock(),
        }

        with patch("common.alerter_helpers.initialization_coordinator.AlerterComponentsBuilder") as mock_builder:
            mock_builder.return_value.build.return_value = mock_components
            with patch("common.alerter_helpers.initialization_coordinator.AlertSender"):
                result = InitializationCoordinator.initialize_components(
                    settings=mock_settings,
                    send_alert_callback=MagicMock(),
                    flush_callback=MagicMock(),
                    ensure_proc_callback=MagicMock(),
                )

                assert "delivery_manager" in result
                assert "command_registry" in result
                assert result["delivery_manager"] is mock_delivery_manager

    def test_excludes_telegram_components_when_disabled(self) -> None:
        """Test excludes telegram components when disabled."""
        mock_settings = MagicMock()
        mock_components = {
            "telegram_enabled": False,
            "authorized_user_ids": set(),
        }

        with patch("common.alerter_helpers.initialization_coordinator.AlerterComponentsBuilder") as mock_builder:
            mock_builder.return_value.build.return_value = mock_components

            result = InitializationCoordinator.initialize_components(
                settings=mock_settings,
                send_alert_callback=MagicMock(),
                flush_callback=MagicMock(),
                ensure_proc_callback=MagicMock(),
            )

            assert "delivery_manager" not in result
            assert "command_registry" not in result

    def test_creates_alert_sender_when_telegram_enabled(self) -> None:
        """Test creates AlertSender when telegram enabled."""
        mock_settings = MagicMock()
        mock_components = {
            "telegram_enabled": True,
            "authorized_user_ids": {123},
            "delivery_manager": MagicMock(),
            "command_registry": MagicMock(),
            "command_processor": MagicMock(),
            "polling_coordinator": MagicMock(),
            "price_validation_tracker": MagicMock(),
            "suppression_manager": MagicMock(),
            "alert_throttle": MagicMock(),
        }

        with patch("common.alerter_helpers.initialization_coordinator.AlerterComponentsBuilder") as mock_builder:
            mock_builder.return_value.build.return_value = mock_components
            with patch("common.alerter_helpers.initialization_coordinator.AlertSender") as mock_sender:
                mock_sender.return_value = MagicMock()

                result = InitializationCoordinator.initialize_components(
                    settings=mock_settings,
                    send_alert_callback=MagicMock(),
                    flush_callback=MagicMock(),
                    ensure_proc_callback=MagicMock(),
                )

                assert "alert_sender" in result


class TestInitializationCoordinatorCreateAlertSender:
    """Tests for _create_alert_sender static method."""

    def test_creates_sender_config(self) -> None:
        """Test creates AlertSenderConfig."""
        mock_components = {
            "suppression_manager": MagicMock(),
            "alert_throttle": MagicMock(),
            "authorized_user_ids": {123},
            "delivery_manager": MagicMock(),
        }

        with patch("common.alerter_helpers.initialization_coordinator.AlertSenderConfig") as mock_config:
            with patch("common.alerter_helpers.initialization_coordinator.AlertSender"):
                InitializationCoordinator._create_alert_sender(
                    components=mock_components,
                    send_alert_callback=MagicMock(),
                    ensure_proc_callback=MagicMock(),
                )

                mock_config.assert_called_once()
                call_kwargs = mock_config.call_args[1]
                assert call_kwargs["telegram_enabled"] is True

    def test_returns_alert_sender(self) -> None:
        """Test returns AlertSender instance."""
        mock_components = {
            "suppression_manager": MagicMock(),
            "alert_throttle": MagicMock(),
            "authorized_user_ids": {123},
            "delivery_manager": MagicMock(),
        }
        mock_sender_instance = MagicMock()

        with patch("common.alerter_helpers.initialization_coordinator.AlertSenderConfig"):
            with patch("common.alerter_helpers.initialization_coordinator.AlertSender") as mock_sender:
                mock_sender.return_value = mock_sender_instance

                result = InitializationCoordinator._create_alert_sender(
                    components=mock_components,
                    send_alert_callback=MagicMock(),
                    ensure_proc_callback=MagicMock(),
                )

                assert result is mock_sender_instance
