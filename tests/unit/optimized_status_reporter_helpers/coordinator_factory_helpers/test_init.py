"""Tests for coordinator factory helpers module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.optimized_status_reporter_helpers.coordinator_factory_helpers import (
    StatusReportCollectors,
    create_calculators,
    create_coordinator_with_redis,
    create_formatters_and_printers,
    create_non_redis_collectors,
    create_utility_components,
)


class TestStatusReportCollectors:
    """Tests for StatusReportCollectors dataclass."""

    def test_creates_frozen_dataclass(self) -> None:
        """Creates frozen dataclass with all fields."""
        collectors = StatusReportCollectors(
            service_state_collector=MagicMock(),
            tracker_status_collector=MagicMock(),
            health_snapshot_collector=MagicMock(),
            log_activity_collector=MagicMock(),
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        assert collectors.service_state_collector is not None
        assert collectors.tracker_status_collector is not None
        assert collectors.health_snapshot_collector is not None
        assert collectors.log_activity_collector is not None
        assert collectors.console_section_printer is not None
        assert collectors.weather_section_generator is not None
        assert collectors.data_coercion is not None

    def test_is_frozen(self) -> None:
        """Dataclass is frozen and cannot be modified."""
        collectors = StatusReportCollectors(
            service_state_collector=MagicMock(),
            tracker_status_collector=MagicMock(),
            health_snapshot_collector=MagicMock(),
            log_activity_collector=MagicMock(),
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        with pytest.raises(AttributeError):
            collectors.service_state_collector = MagicMock()


class TestCreateUtilityComponents:
    """Tests for create_utility_components function."""

    def test_returns_three_components(self) -> None:
        """Returns data_coercion, data_formatting, and time_formatter."""
        data_coercion, data_formatting, time_formatter = create_utility_components()

        assert data_coercion is not None
        assert data_formatting is not None
        assert time_formatter is not None

    def test_returns_correct_types(self) -> None:
        """Returns correct types for each component."""
        from common.optimized_status_reporter_helpers.data_coercion import DataCoercion
        from common.optimized_status_reporter_helpers.data_formatting import DataFormatting
        from common.optimized_status_reporter_helpers.time_formatter import TimeFormatter

        data_coercion, data_formatting, time_formatter = create_utility_components()

        assert isinstance(data_coercion, DataCoercion)
        assert isinstance(data_formatting, DataFormatting)
        assert isinstance(time_formatter, TimeFormatter)


class TestCreateCalculators:
    """Tests for create_calculators function."""

    def test_returns_day_night_detector(self) -> None:
        """Returns DayNightDetector instance."""
        from common.optimized_status_reporter_helpers.day_night_detector import (
            DayNightDetector,
        )

        result = create_calculators()

        assert isinstance(result, DayNightDetector)

    def test_loads_weather_station_coordinates(self) -> None:
        """Loads weather station coordinates during creation."""
        day_night_detector = create_calculators()

        assert day_night_detector._station_coordinates is not None


class TestCreateNonRedisCollectors:
    """Tests for create_non_redis_collectors function."""

    def test_returns_four_collectors(self) -> None:
        """Returns four collector instances."""
        process_manager = MagicMock()
        process_manager.services = []
        process_manager.process_info = {}
        health_checker = MagicMock()
        tracker_controller = MagicMock()

        result = create_non_redis_collectors(process_manager, health_checker, tracker_controller)

        assert len(result) == 4

    def test_returns_correct_collector_types(self) -> None:
        """Returns correct types for each collector."""
        from common.optimized_status_reporter_helpers.health_snapshot_collector import (
            HealthSnapshotCollector,
        )
        from common.optimized_status_reporter_helpers.log_activity_collector import (
            LogActivityCollector,
        )
        from common.optimized_status_reporter_helpers.service_state_collector import (
            ServiceStateCollector,
        )
        from common.optimized_status_reporter_helpers.tracker_status_collector import (
            TrackerStatusCollector,
        )

        process_manager = MagicMock()
        process_manager.services = []
        process_manager.process_info = {}
        health_checker = MagicMock()
        tracker_controller = MagicMock()

        (
            service_state,
            tracker_status,
            health_snapshot,
            log_activity,
        ) = create_non_redis_collectors(process_manager, health_checker, tracker_controller)

        assert isinstance(service_state, ServiceStateCollector)
        assert isinstance(tracker_status, TrackerStatusCollector)
        assert isinstance(health_snapshot, HealthSnapshotCollector)
        assert isinstance(log_activity, LogActivityCollector)


class TestCreateFormattersAndPrinters:
    """Tests for create_formatters_and_printers function."""

    def test_function_exists(self) -> None:
        """Function is importable and callable."""
        assert callable(create_formatters_and_printers)

    def test_function_signature(self) -> None:
        """Function accepts expected parameters."""
        import inspect

        sig = inspect.signature(create_formatters_and_printers)
        params = list(sig.parameters.keys())

        assert "process_manager" in params
        assert "data_coercion" in params
        assert "data_formatting" in params
        assert "time_formatter" in params
        assert "day_night_detector" in params


class TestCreateCoordinatorWithRedis:
    """Tests for create_coordinator_with_redis function."""

    @pytest.mark.asyncio
    async def test_creates_coordinator(self) -> None:
        """Creates StatusReportCoordinator with all dependencies."""
        from common.optimized_status_reporter_helpers.status_report_coordinator import (
            StatusReportCoordinator,
        )

        redis_client = AsyncMock()
        process_manager = MagicMock()
        process_manager.services = []
        process_manager.process_info = {}
        health_checker = MagicMock()
        metadata_store = MagicMock()
        tracker_controller = MagicMock()
        collectors = StatusReportCollectors(
            service_state_collector=MagicMock(),
            tracker_status_collector=MagicMock(),
            health_snapshot_collector=MagicMock(),
            log_activity_collector=MagicMock(),
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        result = await create_coordinator_with_redis(
            redis_client,
            process_manager,
            health_checker,
            metadata_store,
            tracker_controller,
            collectors,
        )

        assert isinstance(result, StatusReportCoordinator)

    def test_function_is_async(self) -> None:
        """Function is a coroutine function."""
        import inspect

        assert inspect.iscoroutinefunction(create_coordinator_with_redis)
