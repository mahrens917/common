"""Lifecycle management: stop sentinels and task cancellation."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def send_stop_sentinels(queue: asyncio.Queue, count: int, subscriber_name: str) -> None:
    """Send sentinel values to consumer tasks, draining if queue is full."""
    for _ in range(count):
        try:
            queue.put_nowait(None)
        except asyncio.QueueFull:  # policy_guard: allow-silent-handler
            logger.warning("%s: queue full during stop, draining to send sentinel", subscriber_name)
            try:
                while queue.full():
                    dropped = queue.get_nowait()
                    if dropped is not None and isinstance(dropped, tuple) and dropped:
                        logger.warning("%s: dropped unACKed stream entry %s during shutdown drain", subscriber_name, dropped[0])
                queue.put_nowait(None)
            except (asyncio.QueueEmpty, asyncio.QueueFull):  # policy_guard: allow-silent-handler
                logger.warning("%s: failed to deliver stop sentinel after drain attempt", subscriber_name)


async def cancel_task(task: Optional[asyncio.Task]) -> None:
    """Cancel a single task and suppress CancelledError."""
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:  # policy_guard: allow-silent-handler
        pass


async def cancel_tasks(tasks: list) -> None:
    """Cancel a list of tasks and suppress CancelledError."""
    for task in tasks:
        await cancel_task(task)


__all__ = ["cancel_task", "cancel_tasks", "send_stop_sentinels"]
