from __future__ import annotations

"""Shared helpers for Telegram command handlers."""

from typing import Any, Awaitable, Callable, Dict


class BaseTelegramCommandHandler:
    """Provide shared utilities for Telegram command handlers."""

    def __init__(self, alerter: Any, alert_type: str) -> None:
        self._alerter = alerter
        self._alert_type = alert_type

    async def _send(self, message: str) -> None:
        """Send a message using the configured alerter."""
        await self._alerter.send_alert(message, alert_type=self._alert_type)

    def register_command(
        self,
        command: str,
        handler: Callable[[Dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Register a Telegram command if the alerter supports it."""
        if hasattr(self._alerter, "register_command_handler"):
            self._alerter.register_command_handler(command, handler)

    def create_handler_wrapper(
        self,
        handler: Callable[[Dict[str, Any]], Awaitable[None]],
    ) -> Callable[[Dict[str, Any]], Awaitable[None]]:
        """Wrap a coroutine handler to match the alerter signature."""

        async def _wrapper(update_data: Dict[str, Any]) -> None:
            await handler(update_data)

        return _wrapper


__all__ = ["BaseTelegramCommandHandler"]
