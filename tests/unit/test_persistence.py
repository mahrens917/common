"""Tests for common.persistence SQLite-backed config storage."""

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


def test_create_tables_creates_config_table():
    conn = persistence._get_connection()
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "config" in tables


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


async def test_restore_to_redis_empty_no_pipelines():
    redis = MagicMock()
    redis.pipeline = MagicMock()

    with patch(
        "common.redis_protocol.typing.ensure_awaitable",
        side_effect=lambda x: x,
    ):
        await persistence.restore_to_redis(redis)

    redis.pipeline.assert_not_called()
