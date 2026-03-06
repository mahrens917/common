"""Hybrid stream + timer runner for services that maintain state from
a stream and perform heavy compute on a cadence.

Used by PDF (Deribit stream + BL extraction timer) and claude_runner
(Kalshi market stream + LLM evaluation timer).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from .subscriber import RedisStreamSubscriber, StreamConfig

logger = logging.getLogger(__name__)


@dataclass
class HybridConfig:
    """Configuration for hybrid stream + timer mode."""

    stream_config: StreamConfig
    timer_interval_seconds: int


async def run_hybrid_mode(
    redis_client: Any,
    config: HybridConfig,
    on_update: Callable[[str, dict], Awaitable[None]],
    on_timer: Callable[[], Awaitable[None]],
    *,
    subscriber_name: str = "hybrid",
) -> None:
    """Run a hybrid stream subscriber + periodic timer concurrently.

    ``on_update`` is called for each stream message (lightweight state merge).
    ``on_timer`` fires every ``config.timer_interval_seconds`` (heavy compute).
    Both run concurrently via ``asyncio.gather``.
    """
    subscriber = RedisStreamSubscriber(
        redis_client,
        on_update,
        config=config.stream_config,
        subscriber_name=f"{subscriber_name}-stream",
    )
    await subscriber.start()
    timer_task = asyncio.create_task(
        _timer_loop(config.timer_interval_seconds, on_timer, subscriber_name),
        name=f"{subscriber_name}-timer",
    )

    try:
        all_tasks = [timer_task, *subscriber.consumer_tasks]
        if subscriber.reader_task is not None:
            all_tasks.append(subscriber.reader_task)
        await asyncio.gather(*all_tasks)
    finally:
        timer_task.cancel()
        await subscriber.stop()


async def _timer_loop(
    interval_seconds: int,
    on_timer: Callable[[], Awaitable[None]],
    subscriber_name: str,
) -> None:
    """Periodically call ``on_timer`` at the configured interval."""
    while True:
        await asyncio.sleep(interval_seconds)
        results = await asyncio.gather(on_timer(), return_exceptions=True)
        if results and isinstance(results[0], Exception):
            logger.error("%s timer callback raised: %s", subscriber_name, results[0])


__all__ = ["HybridConfig", "run_hybrid_mode"]
