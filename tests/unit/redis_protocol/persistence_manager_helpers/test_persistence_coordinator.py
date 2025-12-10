from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pytest
import redis.exceptions

from common.redis_protocol.persistence_manager_helpers.persistence_coordinator import (
    PersistenceCoordinator,
)


class _RecordingRedis:
    def __init__(self, side_effects: List[object] | None = None):
        self.side_effects = list(side_effects or [])
        self.calls: list[tuple[str, str]] = []

    async def config_set(self, key: str, value: str):
        self.calls.append((key, value))
        if self.side_effects:
            effect = self.side_effects.pop(0)
            if isinstance(effect, BaseException):
                raise effect
        return "OK"

    async def config_rewrite(self):
        if self.side_effects:
            effect = self.side_effects.pop(0)
            if isinstance(effect, BaseException):
                raise effect
        return "OK"


@pytest.mark.asyncio
async def test_ensure_data_directory_creates_path(tmp_path):
    coordinator = PersistenceCoordinator()
    coordinator.IMMUTABLE_CONFIGS["dir"] = str(tmp_path / "redis_data_dir")

    assert await coordinator.ensure_data_directory() is True
    assert Path(coordinator.IMMUTABLE_CONFIGS["dir"]).exists()


@pytest.mark.asyncio
async def test_ensure_data_directory_handles_os_error(monkeypatch):
    coordinator = PersistenceCoordinator()
    marker = Path(coordinator.IMMUTABLE_CONFIGS["dir"])

    def _raise(_self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "mkdir", _raise)
    assert await coordinator.ensure_data_directory() is False


@pytest.mark.asyncio
async def test_apply_runtime_config_tracks_immutable_and_failures():
    errors = [
        redis.exceptions.ResponseError("immutable config"),
        redis.exceptions.ResponseError("permission denied"),
    ]
    redis_client = _RecordingRedis(side_effects=[errors[0], errors[1]])
    coordinator = PersistenceCoordinator()

    applied, failed, skipped = await coordinator.apply_runtime_config(redis_client)

    # One immutable config skipped, the other counted as failure
    assert applied + failed + skipped == len(coordinator.RUNTIME_PERSISTENCE_CONFIG)
    assert skipped == 1
    assert failed == 1


@pytest.mark.asyncio
async def test_apply_runtime_config_succeeds_without_errors():
    redis_client = _RecordingRedis()
    coordinator = PersistenceCoordinator()

    applied, failed, skipped = await coordinator.apply_runtime_config(redis_client)

    assert applied == len(coordinator.RUNTIME_PERSISTENCE_CONFIG)
    assert failed == 0
    assert skipped == 0
    assert redis_client.calls  # ensures we executed config_set loop


@pytest.mark.asyncio
async def test_persist_config_to_disk_handles_redis_error():
    redis_client = _RecordingRedis(side_effects=[redis.exceptions.RedisError("no disk space")])
    coordinator = PersistenceCoordinator()

    assert await coordinator.persist_config_to_disk(redis_client) is False


def test_log_immutable_configs_logs_all(caplog):
    coordinator = PersistenceCoordinator()
    caplog.set_level("INFO")

    coordinator.log_immutable_configs()

    for key, value in coordinator.IMMUTABLE_CONFIGS.items():
        assert any(key in message and str(value) in message for message in caplog.text.splitlines())
