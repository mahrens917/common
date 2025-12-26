"""Tests for alerter_helpers.command_registration module."""

from unittest.mock import MagicMock

import pytest

from common.alerter_helpers.command_registration import CommandRegistration


class TestCommandRegistrationRegisterCommands:
    """Tests for register_commands method."""

    def test_registers_all_commands(self) -> None:
        """Test registers all expected commands."""
        mock_registry = MagicMock()
        mock_coordinator = MagicMock()

        CommandRegistration.register_commands(mock_registry, mock_coordinator)

        # Verify all commands are registered
        registered_commands = [call[0][0] for call in mock_registry.register_command_handler.call_args_list]
        assert "help" in registered_commands
        assert "load" in registered_commands
        assert "price" in registered_commands
        assert "temp" in registered_commands
        assert "pnl" in registered_commands

    def test_registers_correct_handlers(self) -> None:
        """Test registers correct handlers for each command."""
        mock_registry = MagicMock()
        mock_coordinator = MagicMock()

        CommandRegistration.register_commands(mock_registry, mock_coordinator)

        # Build dict of registered commands -> handlers
        registered = {}
        for call in mock_registry.register_command_handler.call_args_list:
            registered[call[0][0]] = call[0][1]

        assert registered["help"] == mock_coordinator.handle_help
        assert registered["load"] == mock_coordinator.handle_load
        assert registered["price"] == mock_coordinator.handle_price
        assert registered["temp"] == mock_coordinator.handle_temp
        assert registered["pnl"] == mock_coordinator.handle_pnl

    def test_calls_register_correct_number_of_times(self) -> None:
        """Test calls register_command_handler correct number of times."""
        mock_registry = MagicMock()
        mock_coordinator = MagicMock()

        CommandRegistration.register_commands(mock_registry, mock_coordinator)

        assert mock_registry.register_command_handler.call_count == 5
