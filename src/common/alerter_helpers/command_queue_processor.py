"""Sequential command queue processor for Telegram commands."""

from __future__ import annotations

import asyncio
import logging

from ..alerting import AlertSeverity, QueuedCommand

logger = logging.getLogger(__name__)


class CommandQueueProcessor:
    """Processes Telegram commands from queue sequentially."""

    def __init__(self, command_queue: asyncio.Queue, send_alert_callback):
        """
        Initialize command queue processor.

        Args:
            command_queue: Queue of commands to process
            send_alert_callback: Callback to send alert messages
        """
        self.command_queue = command_queue
        self.send_alert_callback = send_alert_callback
        self.is_processing = False
        self.processor_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the command queue processor."""
        if self.processor_task is None or self.processor_task.done():
            self.processor_task = asyncio.create_task(self._process_queue())
            logger.debug("Command queue processor started")

    async def stop(self) -> None:
        """Stop the command queue processor."""
        if self.processor_task and not self.processor_task.done():
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
            logger.info("Command queue processor stopped")

    async def _process_queue(self) -> None:
        """Process commands from the queue sequentially."""
        self.is_processing = True
        logger.debug("Command queue processor running")

        try:
            while True:
                try:
                    # Wait for next command in queue
                    queued_command: QueuedCommand = await self.command_queue.get()

                    logger.debug(f"Processing queued command: /{queued_command.command}")

                    # Execute the command handler
                    try:
                        await queued_command.handler(queued_command.message)
                        logger.debug(f"Successfully processed command: /{queued_command.command}")
                    except (RuntimeError, ValueError, TypeError, KeyError, OSError) as exc:
                        logger.exception("Error executing queued command /%s", queued_command.command)
                        # Send error message to user
                        await self.send_alert_callback(
                            f"Error executing command /{queued_command.command}: {str(exc)}",
                            AlertSeverity.WARNING,
                        )
                    finally:
                        # Mark task as done
                        self.command_queue.task_done()

                except asyncio.CancelledError:
                    logger.info("Command queue processor cancelled")
                    break
                except (OSError, RuntimeError, ValueError) as exc:
                    logger.exception("Error in command queue processor")
                    # Continue processing other commands

        except asyncio.CancelledError:
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            logger.exception("Fatal error in command queue processor")
        finally:
            self.is_processing = False
            logger.info("Command queue processor stopped")
