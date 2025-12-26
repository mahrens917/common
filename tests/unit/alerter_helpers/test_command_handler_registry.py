"""Tests for alerter_helpers.command_handler_registry module."""

from unittest.mock import MagicMock

from common.alerter_helpers.command_handler_registry import CommandHandlerRegistry


class TestCommandHandlerRegistryInit:
    """Tests for CommandHandlerRegistry initialization."""

    def test_creates_empty_handlers_dict(self) -> None:
        """Test creates empty command_handlers dict."""
        registry = CommandHandlerRegistry()
        assert registry.command_handlers == {}

    def test_creates_instance(self) -> None:
        """Test creates instance."""
        registry = CommandHandlerRegistry()
        assert registry is not None


class TestCommandHandlerRegistryRegisterCommandHandler:
    """Tests for register_command_handler method."""

    def test_registers_handler(self) -> None:
        """Test registers handler for command."""
        registry = CommandHandlerRegistry()
        handler = MagicMock()

        registry.register_command_handler("start", handler)

        assert registry.command_handlers["start"] is handler

    def test_overwrites_existing_handler(self) -> None:
        """Test overwrites existing handler for same command."""
        registry = CommandHandlerRegistry()
        handler1 = MagicMock()
        handler2 = MagicMock()

        registry.register_command_handler("status", handler1)
        registry.register_command_handler("status", handler2)

        assert registry.command_handlers["status"] is handler2

    def test_registers_multiple_commands(self) -> None:
        """Test registers multiple different commands."""
        registry = CommandHandlerRegistry()
        handler1 = MagicMock()
        handler2 = MagicMock()

        registry.register_command_handler("start", handler1)
        registry.register_command_handler("stop", handler2)

        assert len(registry.command_handlers) == 2
        assert registry.command_handlers["start"] is handler1
        assert registry.command_handlers["stop"] is handler2


class TestCommandHandlerRegistryGetHandler:
    """Tests for get_handler method."""

    def test_returns_registered_handler(self) -> None:
        """Test returns registered handler."""
        registry = CommandHandlerRegistry()
        handler = MagicMock()
        registry.register_command_handler("help", handler)

        result = registry.get_handler("help")

        assert result is handler

    def test_returns_none_for_unregistered_command(self) -> None:
        """Test returns None for unregistered command."""
        registry = CommandHandlerRegistry()

        result = registry.get_handler("unknown")

        assert result is None

    def test_returns_none_after_empty_init(self) -> None:
        """Test returns None when no handlers registered."""
        registry = CommandHandlerRegistry()

        result = registry.get_handler("any")

        assert result is None


class TestCommandHandlerRegistryHasHandler:
    """Tests for has_handler method."""

    def test_returns_true_for_registered_command(self) -> None:
        """Test returns True for registered command."""
        registry = CommandHandlerRegistry()
        registry.register_command_handler("status", MagicMock())

        result = registry.has_handler("status")

        assert result is True

    def test_returns_false_for_unregistered_command(self) -> None:
        """Test returns False for unregistered command."""
        registry = CommandHandlerRegistry()

        result = registry.has_handler("unknown")

        assert result is False

    def test_returns_false_for_empty_registry(self) -> None:
        """Test returns False when registry is empty."""
        registry = CommandHandlerRegistry()

        result = registry.has_handler("any")

        assert result is False


class TestCommandHandlerRegistryGetAllCommands:
    """Tests for get_all_commands method."""

    def test_returns_empty_list_when_no_handlers(self) -> None:
        """Test returns empty list when no handlers registered."""
        registry = CommandHandlerRegistry()

        result = registry.get_all_commands()

        assert result == []

    def test_returns_list_of_commands(self) -> None:
        """Test returns list of registered command names."""
        registry = CommandHandlerRegistry()
        registry.register_command_handler("start", MagicMock())
        registry.register_command_handler("stop", MagicMock())
        registry.register_command_handler("status", MagicMock())

        result = registry.get_all_commands()

        assert len(result) == 3
        assert "start" in result
        assert "stop" in result
        assert "status" in result

    def test_returns_list_type(self) -> None:
        """Test returns list type."""
        registry = CommandHandlerRegistry()
        registry.register_command_handler("test", MagicMock())

        result = registry.get_all_commands()

        assert isinstance(result, list)
