"""Tests for process monitor initialization module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.process_monitor_helpers.initialization import Initialization


class TestInitialization:
    """Tests for Initialization class."""

    @pytest.mark.asyncio
    async def test_perform_initial_scan_calls_coordinator(self) -> None:
        """Calls scan coordinator to perform full scan."""
        scan_coordinator = MagicMock()
        scan_coordinator.perform_full_scan = AsyncMock(return_value=({}, {}, [], 1234567890.0))
        process_cache = {}
        service_cache = {}
        redis_processes = []

        result = await Initialization.perform_initial_scan(
            scan_coordinator, process_cache, service_cache, redis_processes
        )

        scan_coordinator.perform_full_scan.assert_called_once_with(
            process_cache, service_cache, redis_processes
        )
        assert len(result) == 4

    @pytest.mark.asyncio
    async def test_perform_initial_scan_returns_result(self) -> None:
        """Returns result from scan coordinator."""
        scan_coordinator = MagicMock()
        expected_cache = {"pid1": MagicMock()}
        expected_service = {"service1": MagicMock()}
        expected_redis = [MagicMock()]
        expected_timestamp = 1234567890.0
        scan_coordinator.perform_full_scan = AsyncMock(
            return_value=(expected_cache, expected_service, expected_redis, expected_timestamp)
        )

        result = await Initialization.perform_initial_scan(scan_coordinator, {}, {}, [])

        proc_cache, svc_cache, redis_procs, timestamp = result
        assert proc_cache == expected_cache
        assert svc_cache == expected_service
        assert redis_procs == expected_redis
        assert timestamp == expected_timestamp
