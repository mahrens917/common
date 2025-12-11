import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.websocket.connection_health_monitor_helpers.monitor_lifecycle import (
    MonitorLifecycle,
)


class TestMonitorLifecycle:
    @pytest.fixture
    def lifecycle(self):
        return MonitorLifecycle("test_service", 0.1)  # fast interval for tests

    @pytest.mark.asyncio
    async def test_start_monitoring_success(self, lifecycle):
        callback = AsyncMock()

        await lifecycle.start_monitoring(callback)
        assert lifecycle._monitoring_task is not None

        # Let it run for a bit
        await asyncio.sleep(0)

        await lifecycle.stop_monitoring()
        assert lifecycle._monitoring_task is None
        assert callback.call_count >= 1

    @pytest.mark.asyncio
    async def test_start_monitoring_already_started(self, lifecycle):
        lifecycle._monitoring_task = Mock()  # Fake existing task
        callback = AsyncMock()

        with patch("common.websocket.connection_health_monitor_helpers.monitor_lifecycle.logger") as mock_logger:
            await lifecycle.start_monitoring(callback)
            mock_logger.warning.assert_called_with("test_service health monitoring already started")

    @pytest.mark.asyncio
    async def test_stop_monitoring_not_started(self, lifecycle):
        await lifecycle.stop_monitoring()
        # Should not raise

    @pytest.mark.asyncio
    async def test_monitor_loop_connection_error(self, lifecycle):
        callback = AsyncMock(side_effect=ConnectionError("Fatal error"))

        # We need to intercept the task to prevent it from crashing the test loop unhandled if we just create_task
        # But MonitorLifecycle.start_monitoring uses create_task.
        # We can call _monitor_loop directly to test exception handling.

        with pytest.raises(ConnectionError):
            await lifecycle._monitor_loop(callback)

    @pytest.mark.asyncio
    async def test_monitor_loop_cancelled(self, lifecycle):
        callback = AsyncMock()

        task = asyncio.create_task(lifecycle._monitor_loop(callback))
        await asyncio.sleep(0)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify it handled cancellation gracefully (by checking logs if we could, or just by not raising other errors)
