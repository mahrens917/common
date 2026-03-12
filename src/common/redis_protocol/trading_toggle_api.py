"""
Per-Algo Trading Toggle API

Provides Redis-based per-algo, per-mode trading configuration:
- enable/disable per algo per mode
- sample_rate per algo per mode (execute 1-in-N valid opportunities randomly)
- max_contracts per algo per mode

Redis key patterns:
  config:trading:algo:{algo}:{mode}                 (enabled toggle)
  config:trading:algo:{algo}:{mode}:sample_rate
  config:trading:algo:{algo}:{mode}:max_contracts
  stats:signals:daily:{algo}:{YYYY-MM-DD}           (string counter; daily count with 48h TTL)
  stats:validated:daily:{algo}:{YYYY-MM-DD}          (string counter; daily count with 48h TTL)
  stats:trades:daily:{algo}:{YYYY-MM-DD}             (string counter; daily count with 48h TTL)

Defaults: paper = all ON, live = all OFF; sample_rate = 100; max_contracts = 1
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List

from common.truthy import pick_if

from .typing import ensure_awaitable

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


def _persist_config(key: str, value: str) -> None:
    """Best-effort persist config key to SQLite."""
    from common.persistence import save_config

    save_config(key, value)


def _persist_config_batch(items: List[tuple[str, str]]) -> None:
    """Best-effort persist multiple config keys to SQLite."""
    from common.persistence import save_config_batch

    save_config_batch(items)


ALGO_TRADING_KEY_PREFIX = "config:trading:algo"
SIGNAL_COUNT_KEY_PREFIX = "stats:signals:daily"
VALIDATED_COUNT_KEY_PREFIX = "stats:validated:daily"
TRADE_COUNT_KEY_PREFIX = "stats:trades:daily"

_MODE_DEFAULTS: Dict[str, bool] = {
    "paper": True,
    "live": False,
}

_DEFAULT_SAMPLE_RATE = 100
_DEFAULT_MAX_CONTRACTS = 1

_SECONDS_PER_DAY = 86400
_COUNTER_TTL_SECONDS = 172800  # 48h — covers today + yesterday
_SIGNAL_COUNT_ABSENT = 0


@dataclass(frozen=True)
class AlgoTradingConfig:
    """Per-algo, per-mode trading configuration."""

    enabled: bool
    sample_rate: int
    max_contracts: int


def _algo_key(algo: str, mode: str) -> str:
    """Build the Redis key for an algo/mode enabled toggle."""
    return f"{ALGO_TRADING_KEY_PREFIX}:{algo}:{mode}"


def _algo_config_key(algo: str, mode: str, field: str) -> str:
    """Build the Redis key for an algo/mode config field."""
    return f"{ALGO_TRADING_KEY_PREFIX}:{algo}:{mode}:{field}"


def _date_str(ts: float) -> str:
    """Format a unix timestamp as YYYY-MM-DD in UTC."""
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


def _signal_count_key(algo: str, date: str) -> str:
    """Build the Redis key for a daily signal counter."""
    return f"{SIGNAL_COUNT_KEY_PREFIX}:{algo}:{date}"


def _validated_count_key(algo: str, date: str) -> str:
    """Build the Redis key for a daily validated signal counter."""
    return f"{VALIDATED_COUNT_KEY_PREFIX}:{algo}:{date}"


def _trade_count_key(algo: str, date: str) -> str:
    """Build the Redis key for a daily trade counter."""
    return f"{TRADE_COUNT_KEY_PREFIX}:{algo}:{date}"


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
    key = _algo_key(algo, mode)
    await ensure_awaitable(redis.set(key, value))
    _persist_config(key, value)
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
    _persist_config_batch([(_algo_key(algo, mode), value) for algo in algos])
    status = pick_if(enabled, lambda: "ENABLED", lambda: "DISABLED")
    logger.info("Trading %s for all algos in mode=%s", status, mode)


async def get_algo_sample_rate(redis: "Redis", algo: str, mode: str) -> int:
    """Get sample rate for a specific algo/mode.

    Returns parsed int or default 100 when key is missing.
    """
    value = await ensure_awaitable(redis.get(_algo_config_key(algo, mode, "sample_rate")))
    if value is None:
        return _DEFAULT_SAMPLE_RATE
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return int(value)


async def set_algo_sample_rate(redis: "Redis", algo: str, mode: str, rate: int) -> None:
    """Set sample rate for a specific algo/mode."""
    _validate_positive_int(rate, "sample_rate")
    key = _algo_config_key(algo, mode, "sample_rate")
    await ensure_awaitable(redis.set(key, str(rate)))
    _persist_config(key, str(rate))
    logger.info("Sample rate set to %d for algo=%s mode=%s", rate, algo, mode)


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
    key = _algo_config_key(algo, mode, "max_contracts")
    await ensure_awaitable(redis.set(key, str(contracts)))
    _persist_config(key, str(contracts))
    logger.info("Max contracts set to %d for algo=%s mode=%s", contracts, algo, mode)


async def get_all_algo_trading_config(redis: "Redis", algos: List[str], mode: str) -> Dict[str, AlgoTradingConfig]:
    """Get full trading config for all algos in a single pipeline read.

    Returns dict mapping algo name to AlgoTradingConfig (enabled + sample_rate + max_contracts).
    """
    pipe = redis.pipeline()
    for algo in algos:
        pipe.get(_algo_key(algo, mode))
        pipe.get(_algo_config_key(algo, mode, "sample_rate"))
        pipe.get(_algo_config_key(algo, mode, "max_contracts"))
    results = await ensure_awaitable(pipe.execute())

    _FIELDS_PER_ALGO = 3
    configs: Dict[str, AlgoTradingConfig] = {}
    for idx, algo in enumerate(algos):
        base = idx * _FIELDS_PER_ALGO
        enabled = _parse_bool(results[base], mode)
        sample_rate_raw = results[base + 1]
        max_contracts_raw = results[base + 2]
        sample_rate = int(sample_rate_raw) if sample_rate_raw is not None else _DEFAULT_SAMPLE_RATE
        max_contracts = int(max_contracts_raw) if max_contracts_raw is not None else _DEFAULT_MAX_CONTRACTS
        configs[algo] = AlgoTradingConfig(enabled=enabled, sample_rate=sample_rate, max_contracts=max_contracts)
    return configs


async def increment_signal_count(redis: "Redis", algo: str) -> int:
    """Increment the daily signal counter. Returns today's count.

    Uses a simple string counter per UTC day with a 48h TTL.
    Constant memory per algo per day (~50 bytes vs 100+ MB for sorted sets).
    """
    now = time.time()
    key = _signal_count_key(algo, _date_str(now))
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, _COUNTER_TTL_SECONDS)
    results = await ensure_awaitable(pipe.execute())
    return int(results[0])


async def get_signal_counts(redis: "Redis", algos: List[str]) -> Dict[str, int]:
    """Get today's signal counts for all algos."""
    today = _date_str(time.time())
    pipe = redis.pipeline()
    for algo in algos:
        pipe.get(_signal_count_key(algo, today))
    results = await ensure_awaitable(pipe.execute())
    counts: Dict[str, int] = {}
    for algo, raw in zip(algos, results):
        counts[algo] = int(raw) if raw is not None else _SIGNAL_COUNT_ABSENT
    return counts


async def increment_validated_count(redis: "Redis", algo: str) -> int:
    """Increment the daily validated signal counter. Returns today's count.

    Uses a simple string counter per UTC day with a 48h TTL.
    """
    now = time.time()
    key = _validated_count_key(algo, _date_str(now))
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, _COUNTER_TTL_SECONDS)
    results = await ensure_awaitable(pipe.execute())
    return int(results[0])


async def get_validated_counts(redis: "Redis", algos: List[str]) -> Dict[str, int]:
    """Get today's validated signal counts for all algos."""
    today = _date_str(time.time())
    pipe = redis.pipeline()
    for algo in algos:
        pipe.get(_validated_count_key(algo, today))
    results = await ensure_awaitable(pipe.execute())
    counts: Dict[str, int] = {}
    for algo, raw in zip(algos, results):
        counts[algo] = int(raw) if raw is not None else _SIGNAL_COUNT_ABSENT
    return counts


async def increment_trade_count(redis: "Redis", algo: str) -> int:
    """Increment the daily trade counter. Returns today's count.

    Uses a simple string counter per UTC day with a 48h TTL.
    """
    now = time.time()
    key = _trade_count_key(algo, _date_str(now))
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, _COUNTER_TTL_SECONDS)
    results = await ensure_awaitable(pipe.execute())
    return int(results[0])


async def get_trade_counts(redis: "Redis", algos: List[str]) -> Dict[str, int]:
    """Get today's trade counts for all algos."""
    today = _date_str(time.time())
    pipe = redis.pipeline()
    for algo in algos:
        pipe.get(_trade_count_key(algo, today))
    results = await ensure_awaitable(pipe.execute())
    counts: Dict[str, int] = {}
    for algo, raw in zip(algos, results):
        counts[algo] = int(raw) if raw is not None else _SIGNAL_COUNT_ABSENT
    return counts


async def delete_old_cooldown_keys(redis: "Redis", algos: List[str]) -> int:
    """Delete legacy cooldown_minutes keys for all algos in both modes.

    Returns the number of keys deleted.
    """
    keys = []
    for algo in algos:
        for mode in _MODE_DEFAULTS:
            keys.append(_algo_config_key(algo, mode, "cooldown_minutes"))
    if not keys:
        return 0
    deleted = await ensure_awaitable(redis.delete(*keys))
    logger.info("Deleted %d legacy cooldown_minutes keys", deleted)
    return deleted


async def reset_daily_counts(redis: "Redis", algos: List[str]) -> int:
    """Delete daily signal and trade count keys for all algos.

    Deletes today's and yesterday's counter keys (48h TTL handles older ones).
    Returns the number of keys deleted.
    """
    if not algos:
        return 0
    now = time.time()
    today = _date_str(now)
    yesterday = _date_str(now - _SECONDS_PER_DAY)
    keys: list[str] = []
    for algo in algos:
        for date in (today, yesterday):
            keys.append(_signal_count_key(algo, date))
            keys.append(_validated_count_key(algo, date))
            keys.append(_trade_count_key(algo, date))
    deleted = await ensure_awaitable(redis.delete(*keys))
    logger.info("Deleted %d daily signal/validated/trade count keys", deleted)
    return deleted


async def initialize_algo_trading_defaults(redis: "Redis", algos: List[str]) -> None:
    """Initialize algo trading keys with defaults (SETNX — won't overwrite existing).

    paper mode: all ON (true)
    live mode: all OFF (false)
    sample_rate: 100
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
            pipe.setnx(_algo_config_key(algo, mode, "sample_rate"), str(_DEFAULT_SAMPLE_RATE))
            pipe.setnx(_algo_config_key(algo, mode, "max_contracts"), str(_DEFAULT_MAX_CONTRACTS))
    await ensure_awaitable(pipe.execute())
    logger.info("Initialized algo trading defaults for %d algos", len(algos))


__all__ = [
    "ALGO_TRADING_KEY_PREFIX",
    "AlgoTradingConfig",
    "SIGNAL_COUNT_KEY_PREFIX",
    "TRADE_COUNT_KEY_PREFIX",
    "VALIDATED_COUNT_KEY_PREFIX",
    "delete_old_cooldown_keys",
    "get_algo_max_contracts",
    "get_algo_sample_rate",
    "get_all_algo_trading_config",
    "get_all_algo_trading_states",
    "get_signal_counts",
    "get_trade_counts",
    "get_validated_counts",
    "increment_signal_count",
    "increment_trade_count",
    "increment_validated_count",
    "initialize_algo_trading_defaults",
    "reset_daily_counts",
    "is_algo_trading_enabled",
    "set_algo_max_contracts",
    "set_algo_sample_rate",
    "set_algo_trading_enabled",
    "set_all_algo_trading_enabled",
    "toggle_algo_trading",
]
