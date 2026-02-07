"""
Per-Algo Trading Toggle API

Provides Redis-based per-algo, per-mode trading enable/disable functionality.
Each algo has independent on/off for paper and live modes.

Redis key pattern: config:trading:algo:{algo}:{mode}
Defaults: paper = all ON, live = all OFF
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List

from common.truthy import pick_if

from .typing import ensure_awaitable

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

ALGO_TRADING_KEY_PREFIX = "config:trading:algo"

_MODE_DEFAULTS: Dict[str, bool] = {
    "paper": True,
    "live": False,
}


def _algo_key(algo: str, mode: str) -> str:
    """Build the Redis key for an algo/mode pair."""
    return f"{ALGO_TRADING_KEY_PREFIX}:{algo}:{mode}"


def _parse_bool(value: bytes | str | None, mode: str) -> bool:
    """Parse a Redis value to bool, using mode-based default when key is missing."""
    if value is None:
        return _MODE_DEFAULTS[mode]
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return str(value).lower() == "true"


async def is_algo_trading_enabled(redis: "Redis", algo: str, mode: str) -> bool:
    """Check if trading is enabled for a specific algo/mode.

    Args:
        redis: Redis client
        algo: Algorithm name (e.g. "peak")
        mode: Trading mode ("paper" or "live")

    Returns:
        True if trading is enabled for this algo/mode
    """
    value = await ensure_awaitable(redis.get(_algo_key(algo, mode)))
    return _parse_bool(value, mode)


async def set_algo_trading_enabled(redis: "Redis", algo: str, mode: str, enabled: bool) -> None:
    """Set trading enabled state for a specific algo/mode.

    Args:
        redis: Redis client
        algo: Algorithm name
        mode: Trading mode
        enabled: Whether trading should be enabled
    """
    value = pick_if(enabled, lambda: "true", lambda: "false")
    await ensure_awaitable(redis.set(_algo_key(algo, mode), value))
    status = pick_if(enabled, lambda: "ENABLED", lambda: "DISABLED")
    logger.info("Trading %s for algo=%s mode=%s", status, algo, mode)


async def toggle_algo_trading(redis: "Redis", algo: str, mode: str) -> bool:
    """Toggle trading for a specific algo/mode.

    Args:
        redis: Redis client
        algo: Algorithm name
        mode: Trading mode

    Returns:
        New trading enabled state after toggle
    """
    current = await is_algo_trading_enabled(redis, algo, mode)
    new_state = not current
    await set_algo_trading_enabled(redis, algo, mode, new_state)
    return new_state


async def get_all_algo_trading_states(redis: "Redis", algos: List[str], mode: str) -> Dict[str, bool]:
    """Get trading states for all algos in a single pipeline read.

    Args:
        redis: Redis client
        algos: List of algorithm names
        mode: Trading mode

    Returns:
        Dict mapping algo name to enabled state
    """
    pipe = redis.pipeline()
    for algo in algos:
        pipe.get(_algo_key(algo, mode))
    results = await ensure_awaitable(pipe.execute())
    return {algo: _parse_bool(value, mode) for algo, value in zip(algos, results)}


async def set_all_algo_trading_enabled(redis: "Redis", algos: List[str], mode: str, enabled: bool) -> None:
    """Set trading enabled for all algos in a single pipeline write.

    Args:
        redis: Redis client
        algos: List of algorithm names
        mode: Trading mode
        enabled: Whether trading should be enabled
    """
    value = pick_if(enabled, lambda: "true", lambda: "false")
    pipe = redis.pipeline()
    for algo in algos:
        pipe.set(_algo_key(algo, mode), value)
    await ensure_awaitable(pipe.execute())
    status = pick_if(enabled, lambda: "ENABLED", lambda: "DISABLED")
    logger.info("Trading %s for all algos in mode=%s", status, mode)


async def initialize_algo_trading_defaults(redis: "Redis", algos: List[str]) -> None:
    """Initialize algo trading keys with defaults (SETNX — won't overwrite existing).

    paper mode: all ON (true)
    live mode: all OFF (false)

    Args:
        redis: Redis client
        algos: List of algorithm names
    """
    pipe = redis.pipeline()
    for algo in algos:
        for mode, enabled in _MODE_DEFAULTS.items():
            value = pick_if(enabled, lambda: "true", lambda: "false")
            pipe.setnx(_algo_key(algo, mode), value)
    await ensure_awaitable(pipe.execute())
    logger.info("Initialized algo trading defaults for %d algos", len(algos))


__all__ = [
    "ALGO_TRADING_KEY_PREFIX",
    "get_all_algo_trading_states",
    "initialize_algo_trading_defaults",
    "is_algo_trading_enabled",
    "set_algo_trading_enabled",
    "set_all_algo_trading_enabled",
    "toggle_algo_trading",
]
