"""Tests for monitoring_control module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.resource_tracker_helpers.delegation.monitoring_control import (
    get_max_cpu_last_minute,
    get_max_ram_last_minute,
    start_per_second_monitoring,
    stop_per_second_monitoring,
)


class TestStartPerSecondMonitoring:
    """Tests for start_per_second_monitoring."""

    @pytest.mark.asyncio
    async def test_returns_early_when_loop_is_none(self) -> None:
        """Returns early when monitoring loop is None."""
        get_cpu_ram = MagicMock()
        await start_per_second_monitoring(None, get_cpu_ram)
        get_cpu_ram.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_start_method_when_available(self) -> None:
        """Calls start method when available on monitoring loop."""
        monitoring_loop = MagicMock()
        monitoring_loop.start = AsyncMock()
        get_cpu_ram = MagicMock()

        await start_per_second_monitoring(monitoring_loop, get_cpu_ram)

        monitoring_loop.start.assert_called_once_with(get_cpu_ram)

    @pytest.mark.asyncio
    async def test_calls_loop_directly_when_callable(self) -> None:
        """Calls monitoring loop directly when it's callable."""
        monitoring_loop = AsyncMock(spec=lambda x: None)
        get_cpu_ram = MagicMock()

        await start_per_second_monitoring(monitoring_loop, get_cpu_ram)

        monitoring_loop.assert_called_once_with(get_cpu_ram)

    @pytest.mark.asyncio
    async def test_logs_error_when_no_callable_handler(self) -> None:
        """Logs error when monitoring loop has no callable handler."""

        class NonCallableLoop:
            """Loop object with no callable handlers."""

        monitoring_loop = NonCallableLoop()
        get_cpu_ram = MagicMock()

        await start_per_second_monitoring(monitoring_loop, get_cpu_ram)


class TestStopPerSecondMonitoring:
    """Tests for stop_per_second_monitoring."""

    @pytest.mark.asyncio
    async def test_returns_early_when_loop_is_none(self) -> None:
        """Returns early when monitoring loop is None."""
        await stop_per_second_monitoring(None)

    @pytest.mark.asyncio
    async def test_calls_stop_method_when_available(self) -> None:
        """Calls stop method when available on monitoring loop."""
        monitoring_loop = MagicMock()
        monitoring_loop.stop = AsyncMock()

        await stop_per_second_monitoring(monitoring_loop)

        monitoring_loop.stop.assert_called_once()


class TestGetMaxCpuLastMinute:
    """Tests for get_max_cpu_last_minute."""

    def test_returns_none_when_loop_is_none(self) -> None:
        """Returns None when monitoring loop is None."""
        result = get_max_cpu_last_minute(None)
        assert result is None

    def test_returns_none_when_method_missing(self) -> None:
        """Returns None when get_max_cpu_last_minute method is missing."""
        monitoring_loop = MagicMock(spec=[])
        result = get_max_cpu_last_minute(monitoring_loop)
        assert result is None

    def test_returns_cpu_value_when_available(self) -> None:
        """Returns CPU value when get_max_cpu_last_minute is available."""
        monitoring_loop = MagicMock()
        monitoring_loop.get_max_cpu_last_minute.return_value = 75.5

        result = get_max_cpu_last_minute(monitoring_loop)

        assert result == 75.5


class TestGetMaxRamLastMinute:
    """Tests for get_max_ram_last_minute."""

    def test_returns_none_when_loop_is_none(self) -> None:
        """Returns None when monitoring loop is None."""
        result = get_max_ram_last_minute(None)
        assert result is None

    def test_returns_none_when_method_missing(self) -> None:
        """Returns None when get_max_ram_last_minute method is missing."""
        monitoring_loop = MagicMock(spec=[])
        result = get_max_ram_last_minute(monitoring_loop)
        assert result is None

    def test_returns_ram_value_when_available(self) -> None:
        """Returns RAM value when get_max_ram_last_minute is available."""
        monitoring_loop = MagicMock()
        monitoring_loop.get_max_ram_last_minute.return_value = 82.3

        result = get_max_ram_last_minute(monitoring_loop)

        assert result == 82.3
