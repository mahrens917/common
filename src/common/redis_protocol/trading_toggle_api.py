"""
Trading Toggle API

Provides Redis-based trading enable/disable functionality.
Allows runtime control of trading via monitor UI (o:on/off command).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from common.truthy import pick_if

from .typing import ensure_awaitable

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

TRADING_ENABLED_KEY = "config:trading:enabled"


async def is_trading_enabled(redis: "Redis") -> bool:
    """
    Check if trading is enabled.

    Args:
        redis: Redis client

    Returns:
        True if trading is enabled, False otherwise (default: False)
    """
    value = await ensure_awaitable(redis.get(TRADING_ENABLED_KEY))
    return _parse_trading_enabled_value(value)


def _parse_trading_enabled_value(value: bytes | str | None) -> bool:
    """Parse the raw Redis value into a boolean."""
    if value is None:
        _none_guard_value = False
        return _none_guard_value
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return str(value).lower() == "true"


async def set_trading_enabled(redis: "Redis", enabled: bool) -> None:
    """
    Set trading enabled state.

    Args:
        redis: Redis client
        enabled: Whether trading should be enabled
    """
    value = pick_if(enabled, lambda: "true", lambda: "false")
    await ensure_awaitable(redis.set(TRADING_ENABLED_KEY, value))
    logger.info("Trading %s", pick_if(enabled, lambda: "ENABLED", lambda: "DISABLED"))


async def toggle_trading(redis: "Redis") -> bool:
    """
    Toggle trading enabled state.

    Args:
        redis: Redis client

    Returns:
        New trading enabled state after toggle
    """
    current = await is_trading_enabled(redis)
    new_state = not current
    await set_trading_enabled(redis, new_state)
    return new_state


__all__ = [
    "TRADING_ENABLED_KEY",
    "is_trading_enabled",
    "set_trading_enabled",
    "toggle_trading",
]
