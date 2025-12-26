"""Tests for alerter_helpers.component_manager module."""

from unittest.mock import MagicMock, patch

import pytest

from common.alerter_helpers.component_manager import ComponentManager


class TestComponentManagerInit:
    """Tests for ComponentManager initialization."""

    @patch("common.alerter_helpers.component_manager.InitializationCoordinator.initialize_components")
    @patch("common.alerter_helpers.component_manager.CommandRegistration.register_commands")
    @patch("common.alerter_helpers.component_manager.ChartManager")
    @patch("common.alerter_helpers.component_manager.CommandCoordinator")
    def test_initializes_with_telegram_enabled(
        self,
        _mock_cmd_coord: MagicMock,
        _mock_chart_mgr: MagicMock,
        mock_register: MagicMock,
        mock_init_components: MagicMock,
    ) -> None:
        """Test initialization with Telegram enabled."""
        mock_settings = MagicMock()
        mock_send_alert = MagicMock()
        mock_flush = MagicMock()
        mock_ensure_proc = MagicMock()
        mock_send_chart = MagicMock()

        mock_init_components.return_value = {
            "telegram_enabled": True,
            "authorized_user_ids": ["123", "456"],
            "delivery_manager": MagicMock(),
            "command_registry": MagicMock(),
            "command_processor": MagicMock(),
            "polling_coordinator": MagicMock(),
            "price_validation_tracker": MagicMock(),
            "alert_sender": MagicMock(),
        }

        manager = ComponentManager(
            mock_settings,
            mock_send_alert,
            mock_flush,
            mock_ensure_proc,
            mock_send_chart,
        )

        assert manager.telegram_enabled is True
        assert manager.authorized_user_ids == ["123", "456"]
        mock_register.assert_called_once()

    @patch("common.alerter_helpers.component_manager.InitializationCoordinator.initialize_components")
    @patch("common.alerter_helpers.component_manager.ChartManager")
    @patch("common.alerter_helpers.component_manager.CommandCoordinator")
    def test_initializes_with_telegram_disabled(
        self,
        _mock_cmd_coord: MagicMock,
        _mock_chart_mgr: MagicMock,
        mock_init_components: MagicMock,
    ) -> None:
        """Test initialization with Telegram disabled."""
        mock_settings = MagicMock()
        mock_send_alert = MagicMock()
        mock_flush = MagicMock()
        mock_ensure_proc = MagicMock()
        mock_send_chart = MagicMock()

        mock_init_components.return_value = {
            "telegram_enabled": False,
            "authorized_user_ids": [],
        }

        manager = ComponentManager(
            mock_settings,
            mock_send_alert,
            mock_flush,
            mock_ensure_proc,
            mock_send_chart,
        )

        assert manager.telegram_enabled is False
        assert manager.authorized_user_ids == []


class TestComponentManagerGetTelegramComponent:
    """Tests for get_telegram_component method."""

    @patch("common.alerter_helpers.component_manager.InitializationCoordinator.initialize_components")
    @patch("common.alerter_helpers.component_manager.CommandRegistration.register_commands")
    @patch("common.alerter_helpers.component_manager.ChartManager")
    @patch("common.alerter_helpers.component_manager.CommandCoordinator")
    def test_returns_component_when_telegram_enabled(
        self,
        _mock_cmd_coord: MagicMock,
        _mock_chart_mgr: MagicMock,
        _mock_register: MagicMock,
        mock_init_components: MagicMock,
    ) -> None:
        """Test returns component when Telegram enabled."""
        mock_delivery_mgr = MagicMock()
        mock_init_components.return_value = {
            "telegram_enabled": True,
            "authorized_user_ids": ["123"],
            "delivery_manager": mock_delivery_mgr,
            "command_registry": MagicMock(),
            "command_processor": MagicMock(),
            "polling_coordinator": MagicMock(),
            "price_validation_tracker": MagicMock(),
            "alert_sender": MagicMock(),
        }

        manager = ComponentManager(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )

        result = manager.get_telegram_component("delivery_mgr")

        assert result == mock_delivery_mgr

    @patch("common.alerter_helpers.component_manager.InitializationCoordinator.initialize_components")
    @patch("common.alerter_helpers.component_manager.ChartManager")
    @patch("common.alerter_helpers.component_manager.CommandCoordinator")
    def test_returns_none_when_telegram_disabled(
        self,
        _mock_cmd_coord: MagicMock,
        _mock_chart_mgr: MagicMock,
        mock_init_components: MagicMock,
    ) -> None:
        """Test returns None when Telegram disabled."""
        mock_init_components.return_value = {
            "telegram_enabled": False,
            "authorized_user_ids": [],
        }

        manager = ComponentManager(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )

        result = manager.get_telegram_component("delivery_mgr")

        assert result is None

    @patch("common.alerter_helpers.component_manager.InitializationCoordinator.initialize_components")
    @patch("common.alerter_helpers.component_manager.CommandRegistration.register_commands")
    @patch("common.alerter_helpers.component_manager.ChartManager")
    @patch("common.alerter_helpers.component_manager.CommandCoordinator")
    def test_returns_none_for_unknown_component(
        self,
        _mock_cmd_coord: MagicMock,
        _mock_chart_mgr: MagicMock,
        _mock_register: MagicMock,
        mock_init_components: MagicMock,
    ) -> None:
        """Test returns None for unknown component name."""
        mock_init_components.return_value = {
            "telegram_enabled": True,
            "authorized_user_ids": ["123"],
            "delivery_manager": MagicMock(),
            "command_registry": MagicMock(),
            "command_processor": MagicMock(),
            "polling_coordinator": MagicMock(),
            "price_validation_tracker": MagicMock(),
            "alert_sender": MagicMock(),
        }

        manager = ComponentManager(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )

        result = manager.get_telegram_component("nonexistent_component")

        assert result is None
