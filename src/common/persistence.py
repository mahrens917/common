"""SQLite-based persistence for trading config.

Provides durable storage for algo trading configuration (toggles, sample
rates, max contracts) that must survive Redis restarts.

All other Redis data (market data, streams, signals, trades) is ephemeral
and rebuilds from exchange connections on service restart.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any, Sequence

logger = logging.getLogger(__name__)

_DB_PATH = Path.home() / "projects" / "monitor" / "data" / "persistent_store.db"

_lock = threading.Lock()
_state: dict[str, sqlite3.Connection | None] = {"connection": None}


def _get_connection() -> sqlite3.Connection:
    if _state["connection"] is not None:
        return _state["connection"]
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    _create_tables(conn)
    _state["connection"] = conn
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS config (" "  key TEXT PRIMARY KEY," "  value TEXT NOT NULL" ")")
    conn.commit()


# ── Config ──────────────────────────────────────────────────────────


def save_config(key: str, value: str) -> None:
    """Persist a single config key-value pair."""
    with _lock:
        conn = _get_connection()
        conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
        conn.commit()


def save_config_batch(items: Sequence[tuple[str, str]]) -> None:
    """Persist multiple config key-value pairs in one transaction."""
    with _lock:
        conn = _get_connection()
        conn.executemany("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", items)
        conn.commit()


def load_all_config() -> dict[str, str]:
    """Load all config key-value pairs."""
    with _lock:
        conn = _get_connection()
        cursor = conn.execute("SELECT key, value FROM config")
        return dict(cursor.fetchall())


# ── Restore to Redis ────────────────────────────────────────────────


async def restore_to_redis(redis: Any) -> None:
    """Restore persisted config from SQLite into Redis.

    Call this on service startup, before initialize_algo_trading_defaults.
    Config keys are restored via SET (so SETNX defaults won't overwrite them).
    """
    from .redis_protocol.typing import ensure_awaitable

    config = load_all_config()
    if config:
        pipe = redis.pipeline()
        for key, value in config.items():
            pipe.set(key, value)
        await ensure_awaitable(pipe.execute())
        logger.info("Restored %d config keys from SQLite", len(config))


__all__ = [
    "load_all_config",
    "restore_to_redis",
    "save_config",
    "save_config_batch",
]
