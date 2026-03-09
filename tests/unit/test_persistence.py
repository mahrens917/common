"""Tests for common.persistence SQLite-backed storage."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common import persistence


@pytest.fixture(autouse=True)
def _reset_state(tmp_path: Path):
    """Reset module-level connection state and redirect DB path for each test."""
    original_conn = persistence._state["connection"]
    original_db = persistence._DB_PATH

    persistence._state["connection"] = None
    persistence._DB_PATH = tmp_path / "test_store.db"

    yield

    if persistence._state["connection"] is not None:
        persistence._state["connection"].close()
    persistence._state["connection"] = original_conn
    persistence._DB_PATH = original_db


# ── _get_connection / lazy init ──────────────────────────────────────


def test_get_connection_creates_db_file():
    conn = persistence._get_connection()
    assert isinstance(conn, sqlite3.Connection)
    assert persistence._DB_PATH.exists()


def test_get_connection_returns_same_instance():
    conn1 = persistence._get_connection()
    conn2 = persistence._get_connection()
    assert conn1 is conn2


def test_create_tables_creates_all_tables():
    conn = persistence._get_connection()
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"config", "paper_trades", "settlements"} <= tables


# ── Config ───────────────────────────────────────────────────────────


def test_save_and_load_config():
    persistence.save_config("key1", "val1")
    result = persistence.load_all_config()
    assert result == {"key1": "val1"}


def test_save_config_overwrites_existing():
    persistence.save_config("k", "v1")
    persistence.save_config("k", "v2")
    assert persistence.load_all_config()["k"] == "v2"


def test_save_config_batch():
    persistence.save_config_batch([("a", "1"), ("b", "2")])
    result = persistence.load_all_config()
    assert result == {"a": "1", "b": "2"}


def test_load_all_config_empty():
    assert persistence.load_all_config() == {}


# ── Paper Trades ──────────────────────────────────────────────────────


def test_save_and_load_paper_trade():
    persistence.save_paper_trade("t1", "paper", "lk1", "tk1", {"field": "val"})
    trades = persistence.load_paper_trades("paper")
    assert len(trades) == 1
    trade_id, list_key, trade_key, data = trades[0]
    assert trade_id == "t1"
    assert list_key == "lk1"
    assert trade_key == "tk1"
    assert data == {"field": "val"}


def test_load_paper_trades_filters_by_mode():
    persistence.save_paper_trade("t1", "paper", "lk1", "tk1", {})
    persistence.save_paper_trade("t2", "live", "lk2", "tk2", {})
    paper = persistence.load_paper_trades("paper")
    live = persistence.load_paper_trades("live")
    assert [t[0] for t in paper] == ["t1"]
    assert [t[0] for t in live] == ["t2"]


def test_load_paper_trades_empty():
    assert persistence.load_paper_trades("paper") == []


def test_clear_paper_trades_returns_count():
    trade_ids = ["t1", "t2"]
    for tid in trade_ids:
        persistence.save_paper_trade(tid, "paper", f"lk{tid}", f"tk{tid}", {})
    count = persistence.clear_paper_trades("paper")
    assert count == len(trade_ids)
    assert persistence.load_paper_trades("paper") == []


def test_clear_paper_trades_only_clears_matching_mode():
    persistence.save_paper_trade("t1", "paper", "lk1", "tk1", {})
    persistence.save_paper_trade("t2", "live", "lk2", "tk2", {})
    persistence.clear_paper_trades("paper")
    assert persistence.load_paper_trades("paper") == []
    assert len(persistence.load_paper_trades("live")) == 1


def test_clear_paper_trades_no_rows():
    assert persistence.clear_paper_trades("paper") == 0


# ── Settlements ───────────────────────────────────────────────────────


def test_save_and_load_settlement():
    persistence.save_settlement("TICKER-A", 75)
    result = persistence.load_settlements()
    assert result == {"TICKER-A": 75}


def test_save_settlement_overwrites():
    persistence.save_settlement("TK", 50)
    persistence.save_settlement("TK", 99)
    assert persistence.load_settlements()["TK"] == 99


def test_load_settlements_empty():
    assert persistence.load_settlements() == {}


def test_clear_settlements_returns_count():
    tickers = {"A": 10, "B": 20}
    for ticker, val in tickers.items():
        persistence.save_settlement(ticker, val)
    count = persistence.clear_settlements()
    assert count == len(tickers)
    assert persistence.load_settlements() == {}


def test_clear_settlements_no_rows():
    assert persistence.clear_settlements() == 0


# ── restore_to_redis ──────────────────────────────────────────────────


async def test_restore_to_redis_config():
    persistence.save_config("cfg_key", "cfg_val")

    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[])
    redis = MagicMock()
    redis.pipeline = MagicMock(return_value=pipe)

    with patch(
        "common.redis_protocol.typing.ensure_awaitable",
        side_effect=lambda x: x,
    ):
        await persistence.restore_to_redis(redis)

    pipe.set.assert_called_once_with("cfg_key", "cfg_val")


async def test_restore_to_redis_trades():
    persistence.save_paper_trade("id1", "paper", "lk", "tk", {"x": "y"})

    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[])
    redis = MagicMock()
    redis.pipeline = MagicMock(return_value=pipe)

    with patch(
        "common.redis_protocol.typing.ensure_awaitable",
        side_effect=lambda x: x,
    ):
        await persistence.restore_to_redis(redis)

    pipe.hset.assert_called_once_with("tk", mapping={"x": "y"})
    pipe.rpush.assert_called_once_with("lk", "id1")


async def test_restore_to_redis_settlements():
    persistence.save_settlement("MY-TK", 42)

    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[])
    redis = MagicMock()
    redis.pipeline = MagicMock(return_value=pipe)

    with patch(
        "common.redis_protocol.typing.ensure_awaitable",
        side_effect=lambda x: x,
    ):
        await persistence.restore_to_redis(redis)

    pipe.set.assert_called_once_with("paper:settlements:kalshi:MY-TK", "42")


async def test_restore_to_redis_empty_no_pipelines():
    redis = MagicMock()
    redis.pipeline = MagicMock()

    with patch(
        "common.redis_protocol.typing.ensure_awaitable",
        side_effect=lambda x: x,
    ):
        await persistence.restore_to_redis(redis)

    redis.pipeline.assert_not_called()
