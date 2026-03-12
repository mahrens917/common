"""SQLite-based persistence for config and paper trade data.

Provides durable storage for data that must survive Redis restarts:
- Trading config (algo toggles, sample rates, max contracts)
- Paper/live trade records and settlements

All other Redis data (market data, streams, signals) is ephemeral
and rebuilds from exchange connections on service restart.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
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
    conn.execute(
        "CREATE TABLE IF NOT EXISTS paper_trades ("
        "  id TEXT PRIMARY KEY,"
        "  mode TEXT NOT NULL,"
        "  list_key TEXT NOT NULL,"
        "  trade_key TEXT NOT NULL,"
        "  data TEXT NOT NULL,"
        "  created_at REAL NOT NULL"
        ")"
    )
    conn.execute("CREATE TABLE IF NOT EXISTS settlements (" "  ticker TEXT PRIMARY KEY," "  settlement_cents INTEGER NOT NULL" ")")
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


# ── Paper Trades ────────────────────────────────────────────────────


def save_paper_trade(trade_id: str, mode: str, list_key: str, trade_key: str, data: dict[str, str]) -> None:
    """Persist a single paper/live trade record."""
    with _lock:
        conn = _get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO paper_trades (id, mode, list_key, trade_key, data, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (trade_id, mode, list_key, trade_key, json.dumps(data), time.time()),
        )
        conn.commit()


def load_paper_trades(mode: str) -> list[tuple[str, str, str, dict[str, str]]]:
    """Load all trades for a mode, ordered newest first.

    Returns list of (trade_id, list_key, trade_key, data_dict).
    """
    with _lock:
        conn = _get_connection()
        cursor = conn.execute(
            "SELECT id, list_key, trade_key, data FROM paper_trades WHERE mode = ? ORDER BY created_at DESC",
            (mode,),
        )
        return [(row[0], row[1], row[2], json.loads(row[3])) for row in cursor.fetchall()]


def clear_paper_trades(mode: str) -> int:
    """Delete all trades for a mode. Returns count deleted."""
    with _lock:
        conn = _get_connection()
        cursor = conn.execute("DELETE FROM paper_trades WHERE mode = ?", (mode,))
        conn.commit()
        return cursor.rowcount


def delete_paper_trades_by_ids(trade_ids: Sequence[str]) -> int:
    """Delete specific trade records by ID. Returns count deleted."""
    if not trade_ids:
        return 0
    with _lock:
        conn = _get_connection()
        placeholders = ",".join("?" for _ in trade_ids)
        cursor = conn.execute(f"DELETE FROM paper_trades WHERE id IN ({placeholders})", list(trade_ids))
        conn.commit()
        return cursor.rowcount


# ── Settlements ─────────────────────────────────────────────────────


def save_settlement(ticker: str, settlement_cents: int) -> None:
    """Persist a settlement price."""
    with _lock:
        conn = _get_connection()
        conn.execute("INSERT OR REPLACE INTO settlements (ticker, settlement_cents) VALUES (?, ?)", (ticker, settlement_cents))
        conn.commit()


def load_settlements() -> dict[str, int]:
    """Load all settlement prices."""
    with _lock:
        conn = _get_connection()
        cursor = conn.execute("SELECT ticker, settlement_cents FROM settlements")
        return dict(cursor.fetchall())


def clear_settlements() -> int:
    """Delete all settlements. Returns count deleted."""
    with _lock:
        conn = _get_connection()
        cursor = conn.execute("DELETE FROM settlements")
        conn.commit()
        return cursor.rowcount


# ── Restore to Redis ────────────────────────────────────────────────


async def restore_to_redis(redis: Any) -> None:
    """Restore all persisted data from SQLite into Redis.

    Call this on service startup, before initialize_algo_trading_defaults.
    Config keys are restored via SET (so SETNX defaults won't overwrite them).
    Paper/live trades are restored as hashes + list entries.
    """
    from .redis_protocol.typing import ensure_awaitable

    config = load_all_config()
    if config:
        pipe = redis.pipeline()
        for key, value in config.items():
            pipe.set(key, value)
        await ensure_awaitable(pipe.execute())
        logger.info("Restored %d config keys from SQLite", len(config))

    for mode in ("paper", "live"):
        trades = load_paper_trades(mode)
        if not trades:
            continue
        list_key = trades[0][1]
        existing_len = await ensure_awaitable(redis.llen(list_key))
        if existing_len > 0:
            logger.info("Skipping %s trade restore: Redis list already has %d entries", mode, existing_len)
            continue
        pipe = redis.pipeline()
        for trade_id, _list_key, trade_key, data in trades:
            pipe.hset(trade_key, mapping=data)
        for trade_id, _list_key, _trade_key, _data in reversed(trades):
            pipe.lpush(list_key, trade_id)
        await ensure_awaitable(pipe.execute())
        logger.info("Restored %d %s trades from SQLite", len(trades), mode)

    settlements = load_settlements()
    if settlements:
        pipe = redis.pipeline()
        for ticker, cents in settlements.items():
            pipe.set(f"paper:settlements:kalshi:{ticker}", str(cents))
        await ensure_awaitable(pipe.execute())
        logger.info("Restored %d settlements from SQLite", len(settlements))


__all__ = [
    "clear_paper_trades",
    "clear_settlements",
    "delete_paper_trades_by_ids",
    "load_all_config",
    "load_paper_trades",
    "load_settlements",
    "restore_to_redis",
    "save_config",
    "save_config_batch",
    "save_paper_trade",
    "save_settlement",
]
