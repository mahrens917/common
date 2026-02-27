"""
Per-Algo Trading Toggle API

Provides Redis-based per-algo, per-mode trading configuration:
- enable/disable per algo per mode
- cooldown_minutes per algo per mode
- max_contracts per algo per mode

Redis key patterns:
  config:trading:algo:{algo}:{mode}                 (enabled toggle)
  config:trading:algo:{algo}:{mode}:cooldown_minutes
  config:trading:algo:{algo}:{mode}:max_contracts

Defaults: paper = all ON, live = all OFF; cooldown = 60 min; max_contracts = 1
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
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

_DEFAULT_COOLDOWN_MINUTES = 60
_DEFAULT_MAX_CONTRACTS = 1


@dataclass(frozen=True)
class AlgoTradingConfig:
    """Per-algo, per-mode trading configuration."""

    enabled: bool
    cooldown_minutes: int
    max_contracts: int


def _algo_key(algo: str, mode: str) -> str:
    """Build the Redis key for an algo/mode enabled toggle."""
    return f"{ALGO_TRADING_KEY_PREFIX}:{algo}:{mode}"


def _algo_config_key(algo: str, mode: str, field: str) -> str:
    """Build the Redis key for an algo/mode config field."""
    return f"{ALGO_TRADING_KEY_PREFIX}:{algo}:{mode}:{field}"


def _validate_positive_int(value: int, field_name: str) -> None:
    """Validate that a value is a positive integer."""
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer, got {value!r}")


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


async def get_algo_cooldown_minutes(redis: "Redis", algo: str, mode: str) -> int:
    """Get cooldown in minutes for a specific algo/mode.

    Returns parsed int or default 60 when key is missing.
    """
    value = await ensure_awaitable(redis.get(_algo_config_key(algo, mode, "cooldown_minutes")))
    if value is None:
        return _DEFAULT_COOLDOWN_MINUTES
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return int(value)


async def set_algo_cooldown_minutes(redis: "Redis", algo: str, mode: str, minutes: int) -> None:
    """Set cooldown in minutes for a specific algo/mode."""
    _validate_positive_int(minutes, "cooldown_minutes")
    await ensure_awaitable(redis.set(_algo_config_key(algo, mode, "cooldown_minutes"), str(minutes)))
    logger.info("Cooldown set to %d min for algo=%s mode=%s", minutes, algo, mode)


async def get_algo_max_contracts(redis: "Redis", algo: str, mode: str) -> int:
    """Get max contracts for a specific algo/mode.

    Returns parsed int or default 1 when key is missing.
    """
    value = await ensure_awaitable(redis.get(_algo_config_key(algo, mode, "max_contracts")))
    if value is None:
        return _DEFAULT_MAX_CONTRACTS
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return int(value)


async def set_algo_max_contracts(redis: "Redis", algo: str, mode: str, contracts: int) -> None:
    """Set max contracts for a specific algo/mode."""
    _validate_positive_int(contracts, "max_contracts")
    await ensure_awaitable(redis.set(_algo_config_key(algo, mode, "max_contracts"), str(contracts)))
    logger.info("Max contracts set to %d for algo=%s mode=%s", contracts, algo, mode)


async def get_all_algo_trading_config(redis: "Redis", algos: List[str], mode: str) -> Dict[str, AlgoTradingConfig]:
    """Get full trading config for all algos in a single pipeline read.

    Returns dict mapping algo name to AlgoTradingConfig (enabled + cooldown + max_contracts).
    """
    pipe = redis.pipeline()
    for algo in algos:
        pipe.get(_algo_key(algo, mode))
        pipe.get(_algo_config_key(algo, mode, "cooldown_minutes"))
        pipe.get(_algo_config_key(algo, mode, "max_contracts"))
    results = await ensure_awaitable(pipe.execute())

    _FIELDS_PER_ALGO = 3
    configs: Dict[str, AlgoTradingConfig] = {}
    for idx, algo in enumerate(algos):
        base = idx * _FIELDS_PER_ALGO
        enabled = _parse_bool(results[base], mode)
        cooldown_raw = results[base + 1]
        max_contracts_raw = results[base + 2]
        cooldown = int(cooldown_raw) if cooldown_raw is not None else _DEFAULT_COOLDOWN_MINUTES
        max_contracts = int(max_contracts_raw) if max_contracts_raw is not None else _DEFAULT_MAX_CONTRACTS
        configs[algo] = AlgoTradingConfig(enabled=enabled, cooldown_minutes=cooldown, max_contracts=max_contracts)
    return configs


async def initialize_algo_trading_defaults(redis: "Redis", algos: List[str]) -> None:
    """Initialize algo trading keys with defaults (SETNX — won't overwrite existing).

    paper mode: all ON (true)
    live mode: all OFF (false)
    cooldown: 60 minutes
    max_contracts: 1

    Args:
        redis: Redis client
        algos: List of algorithm names
    """
    pipe = redis.pipeline()
    for algo in algos:
        for mode, enabled in _MODE_DEFAULTS.items():
            value = pick_if(enabled, lambda: "true", lambda: "false")
            pipe.setnx(_algo_key(algo, mode), value)
            pipe.setnx(_algo_config_key(algo, mode, "cooldown_minutes"), str(_DEFAULT_COOLDOWN_MINUTES))
            pipe.setnx(_algo_config_key(algo, mode, "max_contracts"), str(_DEFAULT_MAX_CONTRACTS))
    await ensure_awaitable(pipe.execute())
    logger.info("Initialized algo trading defaults for %d algos", len(algos))


__all__ = [
    "ALGO_TRADING_KEY_PREFIX",
    "AlgoTradingConfig",
    "get_algo_cooldown_minutes",
    "get_algo_max_contracts",
    "get_all_algo_trading_config",
    "get_all_algo_trading_states",
    "initialize_algo_trading_defaults",
    "is_algo_trading_enabled",
    "set_algo_cooldown_minutes",
    "set_algo_max_contracts",
    "set_algo_trading_enabled",
    "set_all_algo_trading_enabled",
    "toggle_algo_trading",
]
