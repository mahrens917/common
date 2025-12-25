"""Lifecycle helper methods for Alerter."""

import asyncio
import logging

logger = logging.getLogger(__name__)


class LifecycleHelpers:
    """Manages Alerter lifecycle operations."""

    def __init__(self, component_manager):
        """Initialize with component manager."""
        self._mgr = component_manager

    def ensure_proc(self) -> None:
        """Ensure command processor is running."""
        if self._mgr.telegram_enabled:
            self.ensure_processor(self._mgr.cmd_processor)

    async def flush(self) -> None:
        """Flush any pending operations."""
        pass

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.cleanup_resources(self._mgr.telegram_enabled, self._mgr.get_telegram_component("cmd_processor"))

    @staticmethod
    def ensure_processor(command_processor) -> None:
        """
        Ensure command processor is running.

        Args:
            command_processor: Command processor instance to start
        """
        try:
            asyncio.get_running_loop()
            asyncio.create_task(command_processor.start())
        except RuntimeError:  # Expected runtime failure in operation  # policy_guard: allow-silent-handler
            logger.debug("No running event loop, skipping command processor start")

    @staticmethod
    async def cleanup_resources(telegram_enabled: bool, command_processor) -> None:
        """
        Clean up resources.

        Args:
            telegram_enabled: Whether Telegram is enabled
            command_processor: Command processor to stop
        """
        if telegram_enabled and command_processor:
            await command_processor.stop()
