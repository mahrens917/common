"""
Dependency factory for OptimizedStatusReporter.

This factory creates and wires all dependencies needed by OptimizedStatusReporter,
reducing the number of direct instantiations in the main class.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from src.common.health.log_activity_monitor import LogActivityMonitor

from .data_coercion import DataCoercion
from .data_formatting import DataFormatting
from .day_night_detector import DayNightDetector
from .health_snapshot_collector import HealthSnapshotCollector
from .kalshi_market_status_collector import KalshiMarketStatusCollector
from .log_activity_collector import LogActivityCollector
from .log_activity_formatter import LogActivityFormatter
from .message_metrics_collector import MessageMetricsCollector
from .metrics_section_printer import MetricsSectionPrinter
from .moon_phase_calculator import MoonPhaseCalculator
from .price_data_collector import PriceDataCollector
from .process_resource_tracker import ProcessResourceTracker
from .realtime_metrics_collector import RealtimeMetricsCollector
from .redis_key_counter import RedisKeyCounter
from .report_printer_coordinator import ReportPrinterCoordinator
from .section_printer import SectionPrinter
from .service_printer import ServicePrinter
from .service_state_collector import ServiceStateCollector
from .status_data_aggregator import StatusDataAggregator, StatusDataCollectors
from .time_formatter import TimeFormatter
from .tracker_status_collector import TrackerStatusCollector
from .weather_section_generator import WeatherSectionGenerator
from .weather_temperature_collector import WeatherTemperatureCollector


@dataclass
class StatusReporterDependencies:
    """Container for all OptimizedStatusReporter dependencies."""

    aggregator: StatusDataAggregator
    printer: ReportPrinterCoordinator


class StatusReporterDependenciesFactory:
    """Factory for creating OptimizedStatusReporter dependencies."""

    @staticmethod
    def create(
        process_manager,
        health_checker,
        metadata_store,
        tracker_controller,
        emit_status_line: Callable[[str], None],
        logs_directory: Optional[Path] = None,
    ) -> StatusReporterDependencies:
        """
        Create all dependencies for OptimizedStatusReporter.

        Args:
            process_manager: Process manager instance
            health_checker: Health checker instance
            metadata_store: Metadata store instance
            tracker_controller: Tracker controller instance
            emit_status_line: Callback for emitting status lines
            logs_directory: Path to logs directory (default: auto-detected)

        Returns:
            StatusReporterDependencies container with aggregator and printer
        """
        if logs_directory is None:
            project_root = Path(__file__).resolve().parents[2]
            logs_directory = project_root / "logs"

        _log_activity_monitor = LogActivityMonitor(str(logs_directory))

        # Initialize helper modules
        data_coercion = DataCoercion()
        _data_formatter = DataFormatting()
        time_formatter = TimeFormatter()
        log_formatter = LogActivityFormatter(time_formatter)
        resource_tracker = ProcessResourceTracker(process_manager)
        moon_phase_calculator = MoonPhaseCalculator()
        day_night_detector = DayNightDetector(moon_phase_calculator)
        day_night_detector.load_weather_station_coordinates()
        weather_generator = WeatherSectionGenerator(day_night_detector, data_coercion)

        # Initialize collectors
        realtime_collector = RealtimeMetricsCollector()
        collectors = StatusDataCollectors(
            service_collector=ServiceStateCollector(process_manager),
            health_collector=HealthSnapshotCollector(health_checker),
            key_counter=RedisKeyCounter(),
            message_collector=MessageMetricsCollector(realtime_collector, metadata_store),
            price_collector=PriceDataCollector(),
            weather_collector=WeatherTemperatureCollector(),
            log_collector=LogActivityCollector(process_manager),
            tracker_collector=TrackerStatusCollector(process_manager, tracker_controller),
            kalshi_collector=KalshiMarketStatusCollector(),
        )

        # Initialize printers
        section_printer = SectionPrinter(emit_status_line)
        service_printer = ServicePrinter(
            emit_status_line,
            resource_tracker,
            log_formatter,
            data_coercion.bool_or_default,
        )
        metrics_printer = MetricsSectionPrinter(data_coercion)

        # Initialize coordinators
        aggregator = StatusDataAggregator(collectors)
        printer = ReportPrinterCoordinator(
            emit_status_line,
            data_coercion,
            section_printer,
            service_printer,
            metrics_printer,
            weather_generator,
            process_manager,
        )

        return StatusReporterDependencies(aggregator=aggregator, printer=printer)
