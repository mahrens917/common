"""Registry for Telegram command handlers."""

from __future__ import annotations

import logging
from typing import Callable, Dict

logger = logging.getLogger(__name__)


class CommandHandlerRegistry:
    """Registry for mapping command names to handler functions."""

    def __init__(self):
        """Initialize command handler registry."""
        self.command_handlers: Dict[str, Callable] = {}

    def register_command_handler(self, command: str, handler: Callable) -> None:
        """
        Register a handler for a Telegram command.

        Args:
            command: Command string (without leading /)
            handler: Async function to handle the command
        """
        self.command_handlers[command] = handler
        logger.info(f"Registered handler for command: /{command}")

    def get_handler(self, command: str) -> Callable | None:
        """
        Get handler for a command.

        Args:
            command: Command string (without leading /)

        Returns:
            Handler function if registered, None otherwise
        """
        return self.command_handlers.get(command)

    def has_handler(self, command: str) -> bool:
        """
        Check if command has a registered handler.

        Args:
            command: Command string (without leading /)

        Returns:
            True if handler is registered
        """
        return command in self.command_handlers

    def get_all_commands(self) -> list[str]:
        """
        Get list of all registered commands.

        Returns:
            List of command names
        """
        return list(self.command_handlers.keys())
