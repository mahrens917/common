"""Unit tests for process_monitor module."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_get_global_process_monitor_delegates() -> None:
    mock_instance = object()
    mock_get = AsyncMock(return_value=mock_instance)

    # Build a minimal module tree to satisfy the lazy import inside get_global_process_monitor
    monitor_mod = ModuleType("monitor")
    monitor_local_mod = ModuleType("monitor.common_local")
    monitor_pm_mod = ModuleType("monitor.common_local.process_monitor")
    monitor_pm_mod.get_global_process_monitor = mock_get  # type: ignore[attr-defined]

    monitor_mod.common_local = monitor_local_mod  # type: ignore[attr-defined]
    monitor_local_mod.process_monitor = monitor_pm_mod  # type: ignore[attr-defined]

    sys.modules.setdefault("monitor", monitor_mod)
    sys.modules.setdefault("monitor.common_local", monitor_local_mod)
    sys.modules["monitor.common_local.process_monitor"] = monitor_pm_mod

    try:
        from common.process_monitor import get_global_process_monitor

        result = await get_global_process_monitor()
    finally:
        sys.modules.pop("monitor.common_local.process_monitor", None)

    assert result is mock_instance
    mock_get.assert_called_once()
