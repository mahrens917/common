"""Tests for MonitoringLoop."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from common.resource_tracker_helpers.monitoring_loop import MonitoringLoop


class TestMonitoringLoop:
    """Test the monitoring loop."""

    @pytest.fixture
    def cpu_tracker(self):
        """Create a mock CPU tracker."""
        tracker = Mock()
        tracker.record_cpu_usage = AsyncMock()
        return tracker

    @pytest.fixture
    def ram_tracker(self):
        """Create a mock RAM tracker."""
        tracker = Mock()
        tracker.record_ram_usage = AsyncMock()
        return tracker

    @pytest.fixture
    def monitoring_loop(self, cpu_tracker, ram_tracker):
        """Create a MonitoringLoop instance."""
        return MonitoringLoop(cpu_tracker, ram_tracker)

    @pytest.mark.asyncio
    async def test_start_creates_monitoring_task(self, monitoring_loop):
        """Test that start() creates a monitoring task."""
        get_cpu_ram_func = AsyncMock(return_value=(50.0, 1024.0))

        await monitoring_loop.start(get_cpu_ram_func)

        assert monitoring_loop._monitoring_task is not None
        assert isinstance(monitoring_loop._monitoring_task, asyncio.Task)

        # Cleanup
        await monitoring_loop.stop()

    @pytest.mark.asyncio
    async def test_start_returns_if_already_started(self, monitoring_loop):
        """Test that start() returns early if task already exists."""
        get_cpu_ram_func = AsyncMock(return_value=(50.0, 1024.0))

        await monitoring_loop.start(get_cpu_ram_func)
        initial_task = monitoring_loop._monitoring_task

        # Try to start again
        await monitoring_loop.start(get_cpu_ram_func)

        # Should be the same task
        assert monitoring_loop._monitoring_task is initial_task

        # Cleanup
        await monitoring_loop.stop()

    @pytest.mark.asyncio
    async def test_stop_returns_if_not_started(self, monitoring_loop):
        """Test that stop() returns early if no task exists."""
        # Should not raise
        await monitoring_loop.stop()
        assert monitoring_loop._monitoring_task is None

    @pytest.mark.asyncio
    async def test_stop_cancels_task_on_timeout(self, monitoring_loop, monkeypatch):
        """Test that stop() cancels task if it doesn't complete in time."""

        # Create a task that never completes
        async def never_complete():
            while True:
                await asyncio.sleep(10)

        task = asyncio.create_task(never_complete())
        monitoring_loop._monitoring_task = task

        # This should timeout and cancel the task
        await monitoring_loop.stop()

        assert monitoring_loop._monitoring_task is None
        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_monitoring_loop_records_cpu_and_ram(self, monitoring_loop):
        """Test that monitoring loop records CPU and RAM usage."""
        call_count = 0

        async def get_cpu_ram():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                monitoring_loop._stop_monitoring.set()
            return (75.5, 2048.0)

        # Run one iteration
        await monitoring_loop._monitoring_loop(get_cpu_ram)

        monitoring_loop.cpu_tracker.record_cpu_usage.assert_called_with(75.5)
        monitoring_loop.ram_tracker.record_ram_usage.assert_called_with(2048.0)

    @pytest.mark.asyncio
    async def test_monitoring_loop_handles_redis_error(self, monitoring_loop):
        """Test that monitoring loop raises on Redis storage error."""
        get_cpu_ram_func = AsyncMock(return_value=(50.0, 1024.0))
        monitoring_loop.cpu_tracker.record_cpu_usage.side_effect = RuntimeError("Redis error")

        with pytest.raises(RuntimeError, match="Failed to store resource metrics to Redis"):
            await monitoring_loop._monitoring_loop(get_cpu_ram_func)

    @pytest.mark.asyncio
    async def test_monitoring_loop_handles_value_error(self, monitoring_loop):
        """Test that monitoring loop raises on ValueError."""
        get_cpu_ram_func = AsyncMock(return_value=(50.0, 1024.0))
        monitoring_loop.cpu_tracker.record_cpu_usage.side_effect = ValueError("Invalid value")

        with pytest.raises(RuntimeError, match="Failed to store resource metrics to Redis"):
            await monitoring_loop._monitoring_loop(get_cpu_ram_func)

    @pytest.mark.asyncio
    async def test_monitoring_loop_handles_type_error(self, monitoring_loop):
        """Test that monitoring loop raises on TypeError."""
        get_cpu_ram_func = AsyncMock(return_value=(50.0, 1024.0))
        monitoring_loop.ram_tracker.record_ram_usage.side_effect = TypeError("Type error")

        with pytest.raises(RuntimeError, match="Failed to store resource metrics to Redis"):
            await monitoring_loop._monitoring_loop(get_cpu_ram_func)

    @pytest.mark.asyncio
    async def test_monitoring_loop_handles_attribute_error(self, monitoring_loop):
        """Test that monitoring loop raises on AttributeError."""
        get_cpu_ram_func = AsyncMock(return_value=(50.0, 1024.0))
        monitoring_loop.cpu_tracker.record_cpu_usage.side_effect = AttributeError("Missing attr")

        with pytest.raises(RuntimeError, match="Failed to store resource metrics to Redis"):
            await monitoring_loop._monitoring_loop(get_cpu_ram_func)

    @pytest.mark.asyncio
    async def test_monitoring_loop_waits_for_stop_event(self, monitoring_loop):
        """Test that monitoring loop waits for stop event between iterations."""
        call_count = 0

        async def get_cpu_ram():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                monitoring_loop._stop_monitoring.set()
            return (50.0, 1024.0)

        await monitoring_loop._monitoring_loop(get_cpu_ram)

        # Should have been called at least twice
        assert call_count >= 2

    def test_get_max_cpu_last_minute_with_data(self, monitoring_loop):
        """Test getting max CPU usage when data exists."""
        monitoring_loop._cpu_readings.append((1234567890.0, 50.0))
        monitoring_loop._cpu_readings.append((1234567891.0, 75.5))
        monitoring_loop._cpu_readings.append((1234567892.0, 60.0))

        assert monitoring_loop.get_max_cpu_last_minute() == 75.5

    def test_get_max_cpu_last_minute_without_data(self, monitoring_loop):
        """Test getting max CPU usage when no data exists."""
        assert monitoring_loop.get_max_cpu_last_minute() is None

    def test_get_max_ram_last_minute_with_data(self, monitoring_loop):
        """Test getting max RAM usage when data exists."""
        monitoring_loop._ram_readings.append((1234567890.0, 1024.0))
        monitoring_loop._ram_readings.append((1234567891.0, 2048.0))
        monitoring_loop._ram_readings.append((1234567892.0, 1536.0))

        assert monitoring_loop.get_max_ram_last_minute() == 2048.0

    def test_get_max_ram_last_minute_without_data(self, monitoring_loop):
        """Test getting max RAM usage when no data exists."""
        assert monitoring_loop.get_max_ram_last_minute() is None

    @pytest.mark.asyncio
    async def test_call_invokes_monitoring_loop(self, monitoring_loop):
        """Test that __call__ invokes the monitoring loop."""
        call_count = 0

        async def get_cpu_ram():
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                monitoring_loop._stop_monitoring.set()
            return (50.0, 1024.0)

        await monitoring_loop(get_cpu_ram)

        monitoring_loop.cpu_tracker.record_cpu_usage.assert_called()

    @pytest.mark.asyncio
    async def test_monitoring_loop_with_custom_stop_event(self, cpu_tracker, ram_tracker):
        """Test MonitoringLoop with a custom stop event."""
        custom_stop_event = asyncio.Event()
        monitoring_loop = MonitoringLoop(cpu_tracker, ram_tracker, stop_event=custom_stop_event)

        assert monitoring_loop._stop_monitoring is custom_stop_event
