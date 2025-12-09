from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.redis_protocol.persistence_manager_helpers.config_orchestrator import (
    ConfigOrchestrator,
)


@pytest.mark.asyncio
async def test_configure_all_success():
    coordinator = MagicMock()
    coordinator.ensure_data_directory = AsyncMock(return_value=True)
    coordinator.apply_runtime_config = AsyncMock(return_value=(1, 0, 0))
    coordinator.log_immutable_configs = MagicMock()
    coordinator.persist_config_to_disk = AsyncMock()

    snapshot_manager = MagicMock()
    snapshot_manager.configure_save_points = AsyncMock(return_value=True)
    snapshot_manager.force_background_save = AsyncMock()

    orchestrator = ConfigOrchestrator(coordinator, snapshot_manager)

    result = await orchestrator.configure_all(redis=MagicMock())

    assert result is True
    coordinator.ensure_data_directory.assert_awaited_once()
    coordinator.apply_runtime_config.assert_awaited_once()
    snapshot_manager.configure_save_points.assert_awaited_once()
    coordinator.persist_config_to_disk.assert_awaited_once()
    snapshot_manager.force_background_save.assert_awaited_once()


@pytest.mark.asyncio
async def test_configure_all_fails_when_data_directory_missing():
    coordinator = MagicMock()
    coordinator.ensure_data_directory = AsyncMock(return_value=False)
    snapshot_manager = MagicMock()
    orchestrator = ConfigOrchestrator(coordinator, snapshot_manager)

    result = await orchestrator.configure_all(redis=MagicMock())

    assert result is False
    coordinator.apply_runtime_config.assert_not_called()


@pytest.mark.asyncio
async def test_configure_all_returns_false_on_exception():
    coordinator = MagicMock()
    coordinator.ensure_data_directory = AsyncMock(side_effect=RuntimeError("boom"))
    snapshot_manager = MagicMock()
    orchestrator = ConfigOrchestrator(coordinator, snapshot_manager)

    result = await orchestrator.configure_all(redis=MagicMock())

    assert result is False
