"""Unit tests for dependencies_factory."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.common.optimized_status_reporter_helpers.dependencies_factory import (
    StatusReporterDependenciesFactory,
)


class TestStatusReporterDependenciesFactory:
    """Tests for StatusReporterDependenciesFactory."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies for the factory."""
        return {
            "process_manager": Mock(),
            "health_checker": Mock(),
            "metadata_store": Mock(),
            "tracker_controller": Mock(),
            "emit_status_line": Mock(),
            "logs_directory": Path("/tmp/logs"),
        }

    @pytest.fixture
    def mock_internal_imports(self, mocker):
        """Mock internal module imports to prevent actual instantiation."""
        # Patch the imported names *within* the dependencies_factory module
        target_module = "src.common.optimized_status_reporter_helpers.dependencies_factory"

        mocks = {}
        for class_name in [
            "DataCoercion",
            "DataFormatting",
            "TimeFormatter",
            "LogActivityFormatter",
            "ProcessResourceTracker",
            "MoonPhaseCalculator",
            "DayNightDetector",
            "WeatherSectionGenerator",
            "RealtimeMetricsCollector",
            "StatusDataCollectors",
            "ServiceStateCollector",
            "HealthSnapshotCollector",
            "RedisKeyCounter",
            "MessageMetricsCollector",
            "PriceDataCollector",
            "WeatherTemperatureCollector",
            "LogActivityCollector",
            "TrackerStatusCollector",
            "KalshiMarketStatusCollector",
            "SectionPrinter",
            "ServicePrinter",
            "MetricsSectionPrinter",
            "StatusDataAggregator",
            "ReportPrinterCoordinator",
            "LogActivityMonitor",
        ]:
            mocks[class_name] = mocker.patch(f"{target_module}.{class_name}")

        yield mocks

    def test_create_dependencies_with_explicit_logs_directory(
        self, mock_dependencies, mock_internal_imports
    ):
        """Test that create properly instantiates and wires all dependencies with an explicit logs directory."""
        factory_deps = StatusReporterDependenciesFactory.create(**mock_dependencies)

        # Assert correct types are returned
        mock_internal_imports["StatusDataAggregator"].assert_called_once()
        mock_internal_imports["ReportPrinterCoordinator"].assert_called_once()

        # Assert LogActivityMonitor is initialized with the correct path
        mock_internal_imports["LogActivityMonitor"].assert_called_once_with(
            str(mock_dependencies["logs_directory"])
        )

        # Assert DayNightDetector loads coordinates
        mock_internal_imports[
            "DayNightDetector"
        ].return_value.load_weather_station_coordinates.assert_called_once()

        # Assert StatusDataCollectors is called with instantiated collectors
        mock_internal_imports["StatusDataCollectors"].assert_called_once_with(
            service_collector=mock_internal_imports["ServiceStateCollector"].return_value,
            health_collector=mock_internal_imports["HealthSnapshotCollector"].return_value,
            key_counter=mock_internal_imports["RedisKeyCounter"].return_value,
            message_collector=mock_internal_imports["MessageMetricsCollector"].return_value,
            price_collector=mock_internal_imports["PriceDataCollector"].return_value,
            weather_collector=mock_internal_imports["WeatherTemperatureCollector"].return_value,
            log_collector=mock_internal_imports["LogActivityCollector"].return_value,
            tracker_collector=mock_internal_imports["TrackerStatusCollector"].return_value,
            kalshi_collector=mock_internal_imports["KalshiMarketStatusCollector"].return_value,
        )

        # Assert ReportPrinterCoordinator is called with instantiated printers and other deps
        mock_internal_imports["ReportPrinterCoordinator"].assert_called_once_with(
            mock_dependencies["emit_status_line"],
            mock_internal_imports["DataCoercion"].return_value,
            mock_internal_imports["SectionPrinter"].return_value,
            mock_internal_imports["ServicePrinter"].return_value,
            mock_internal_imports["MetricsSectionPrinter"].return_value,
            mock_internal_imports["WeatherSectionGenerator"].return_value,
            mock_dependencies["process_manager"],
        )

        assert factory_deps.aggregator == mock_internal_imports["StatusDataAggregator"].return_value
        assert (
            factory_deps.printer == mock_internal_imports["ReportPrinterCoordinator"].return_value
        )

    def test_create_dependencies_without_explicit_logs_directory(
        self, mock_dependencies, mock_internal_imports
    ):
        """Test that create properly determines logs directory when not explicit."""
        mock_dependencies["logs_directory"] = None

        # Patch the Path(__file__).resolve().parents[2] to control expected path
        with patch.object(
            Path,
            "resolve",
            return_value=Path(
                "/root/project/src/common/optimized_status_reporter_helpers/dependencies_factory.py"
            ),
        ) as mock_resolve:
            StatusReporterDependenciesFactory.create(**mock_dependencies)

            expected_logs_dir = Path("/root/project/src/logs")
            mock_internal_imports["LogActivityMonitor"].assert_called_once_with(
                str(expected_logs_dir)
            )
