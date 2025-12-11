"""Unit tests for initialization."""

import asyncio
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from common.optimized_status_reporter_helpers.initialization import (
    StatusReporterInitializer,
)


class TestStatusReporterInitializer:
    """Tests for StatusReporterInitializer."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies for initialize_components."""
        return {
            "process_manager": Mock(),
            "health_checker": Mock(),
            "metadata_store": Mock(),
            "tracker_controller": Mock(),
            "emit_fn": Mock(),
        }

    @pytest.fixture(autouse=True)
    def mock_internal_modules(self, mocker):
        """Mock internal module imports to prevent actual instantiation."""
        # List all classes imported in initialize_components that need to be mocked
        classes_to_mock = [
            "LogActivityMonitor",
            "DataCoercion",
            "DataFormatter",
            "DayNightDetector",
            "LogActivityFormatter",
            "ProcessResourceTracker",
            "WeatherSectionGenerator",
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
            "RealtimeMetricsCollector",
            "MoonPhaseCalculator",
            "TimeFormatter",
        ]
        mock_objects = {}
        for cls_name in classes_to_mock:
            # Patch each class where it's imported in the initialization module
            mock_objects[cls_name] = mocker.patch(f"common.optimized_status_reporter_helpers.initialization.{cls_name}")
        return mock_objects

    def test_initialize_components(self, mock_dependencies, mock_internal_modules):
        """Test initialize_components instantiates and returns all components."""
        # Mock Path(__file__).resolve().parents[2] for logs_dir calculation
        with patch.object(
            Path,
            "resolve",
            return_value=Path("/root/project/src/common/optimized_status_reporter_helpers/initialization.py"),
        ):
            components = StatusReporterInitializer.initialize_components(**mock_dependencies)

        mock_internal_modules["LogActivityMonitor"].assert_called_once_with("/root/project/src/logs")
        mock_internal_modules["DataCoercion"].assert_called_once()
        mock_internal_modules["DataFormatter"].assert_called_once()
        assert components["data_formatter"] == mock_internal_modules["DataFormatter"].return_value
        mock_internal_modules["LogActivityCollector"].assert_called_once_with(mock_dependencies["process_manager"])
        mock_internal_modules["MessageMetricsCollector"].assert_called_once_with(
            mock_internal_modules["RealtimeMetricsCollector"].return_value,
            mock_dependencies["metadata_store"],
        )
        mock_internal_modules["WeatherSectionGenerator"].assert_called_once_with(
            mock_internal_modules["DayNightDetector"].return_value,
            mock_internal_modules["DataCoercion"].return_value,
        )
        mock_internal_modules["LogActivityFormatter"].assert_called_once_with(mock_internal_modules["TimeFormatter"].return_value)
        mock_internal_modules["ServicePrinter"].assert_called_once_with(
            mock_dependencies["emit_fn"],
            mock_internal_modules["ProcessResourceTracker"].return_value,
            mock_internal_modules["LogActivityFormatter"].return_value,
            mock_internal_modules["DataCoercion"].return_value.bool_or_default,
        )
        mock_internal_modules["MetricsSectionPrinter"].assert_called_once_with(mock_internal_modules["DataCoercion"].return_value)
        mock_internal_modules["TrackerStatusCollector"].assert_called_once_with(
            mock_dependencies["process_manager"],
            mock_dependencies["tracker_controller"],
        )

        for mock_cls in mock_internal_modules.values():
            mock_cls.assert_called_once()

        expected_keys = [
            "logs_directory",
            "log_activity_monitor",
            "data_coercion",
            "data_formatter",
            "log_formatter",
            "resource_tracker",
            "weather_generator",
            "service_collector",
            "health_collector",
            "key_counter",
            "message_collector",
            "price_collector",
            "weather_collector",
            "log_collector",
            "tracker_collector",
            "kalshi_collector",
            "section_printer",
            "service_printer",
            "metrics_printer",
        ]
        assert sorted(list(components.keys())) == sorted(expected_keys)

    def test_initialize_kalshi_state(self):
        """Test initialize_kalshi_state returns None and an asyncio.Lock."""
        client, lock = StatusReporterInitializer.initialize_kalshi_state()
        assert client is None
        assert isinstance(lock, asyncio.Lock)

    def test_initialize_instance_attributes(self, mock_dependencies, mock_internal_modules):
        """Test initialize_instance_attributes sets attributes on the instance."""
        mock_instance = Mock()
        mock_instance._emit_status_line = mock_dependencies["emit_fn"]

        # Mock initialize_kalshi_state
        with patch(
            "common.optimized_status_reporter_helpers.initialization.StatusReporterInitializer.initialize_kalshi_state",
            return_value=("mock_client", Mock(spec=asyncio.Lock)),
        ) as mock_init_kalshi:
            # Mock initialize_components
            mock_components_return = {
                "logs_directory": Path("/mock/logs"),
                "log_activity_monitor": mock_internal_modules["LogActivityMonitor"].return_value,
                "data_coercion": mock_internal_modules["DataCoercion"].return_value,
                # Add more mocks for components to fill the return dictionary
                **{k.lower(): v.return_value for k, v in mock_internal_modules.items() if k not in ["LogActivityMonitor", "DataCoercion"]},
            }
            # For specific ones like data_formatter, we need to map the alias
            if "data_formatter" in mock_components_return:
                mock_components_return["data_formatter"] = mock_internal_modules["DataFormatter"].return_value

            with patch(
                "common.optimized_status_reporter_helpers.initialization.StatusReporterInitializer.initialize_components",
                return_value=mock_components_return,
            ) as mock_init_components:
                call_args = {k: v for k, v in mock_dependencies.items() if k != "emit_fn"}
                StatusReporterInitializer.initialize_instance_attributes(mock_instance, **call_args)

                # Assert external dependencies are set directly
                assert mock_instance.process_manager == mock_dependencies["process_manager"]
                assert mock_instance.health_checker == mock_dependencies["health_checker"]
                assert mock_instance.metadata_store == mock_dependencies["metadata_store"]
                assert mock_instance.tracker_controller == mock_dependencies["tracker_controller"]

                # Assert kalshi state is set
                assert mock_instance._kalshi_client == "mock_client"
                assert isinstance(mock_instance._kalshi_client_lock, asyncio.Lock)

                # Assert components are set as _prefixed attributes
                for key, value in mock_components_return.items():
                    assert getattr(mock_instance, f"_{key}") == value
