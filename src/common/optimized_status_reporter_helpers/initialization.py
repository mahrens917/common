"""Initialize all collectors and helpers for OptimizedStatusReporter."""

import asyncio
from pathlib import Path

from common.health.log_activity_monitor import LogActivityMonitor

from .data_coercion import DataCoercion
from .data_formatting import DataFormatting as DataFormatter
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
from .section_printer import SectionPrinter
from .service_printer import ServicePrinter
from .service_state_collector import ServiceStateCollector
from .time_formatter import TimeFormatter
from .tracker_status_collector import TrackerStatusCollector
from .weather_section_generator import WeatherSectionGenerator
from .weather_temperature_collector import WeatherTemperatureCollector


class StatusReporterInitializer:
    """Initialize all components for OptimizedStatusReporter."""

    @staticmethod
    def initialize_components(process_manager, health_checker, metadata_store, tracker_controller, emit_fn):
        """Initialize all collectors, formatters, and printers."""
        logs_dir = Path(__file__).resolve().parents[2] / "logs"
        log_activity_monitor = LogActivityMonitor(str(logs_dir))

        data_coercion = DataCoercion()
        data_formatter = DataFormatter()
        time_formatter = TimeFormatter()
        log_formatter = LogActivityFormatter(time_formatter)
        resource_tracker = ProcessResourceTracker(process_manager)
        moon_phase_calculator = MoonPhaseCalculator()
        day_night_detector = DayNightDetector(moon_phase_calculator)
        day_night_detector.load_weather_station_coordinates()
        weather_generator = WeatherSectionGenerator(day_night_detector, data_coercion)
        realtime_metrics_collector = RealtimeMetricsCollector()

        service_collector = ServiceStateCollector(process_manager)
        health_collector = HealthSnapshotCollector(health_checker)
        key_counter = RedisKeyCounter()
        message_collector = MessageMetricsCollector(realtime_metrics_collector, metadata_store)
        price_collector = PriceDataCollector()
        weather_collector = WeatherTemperatureCollector()
        log_collector = LogActivityCollector(process_manager)
        tracker_collector = TrackerStatusCollector(process_manager, tracker_controller)
        kalshi_collector = KalshiMarketStatusCollector()

        section_printer = SectionPrinter(emit_fn)
        service_printer = ServicePrinter(emit_fn, resource_tracker, log_formatter, data_coercion.bool_or_default)
        metrics_printer = MetricsSectionPrinter(data_coercion)

        return {
            "logs_directory": logs_dir,
            "log_activity_monitor": log_activity_monitor,
            "data_coercion": data_coercion,
            "data_formatter": data_formatter,
            "log_formatter": log_formatter,
            "resource_tracker": resource_tracker,
            "weather_generator": weather_generator,
            "service_collector": service_collector,
            "health_collector": health_collector,
            "key_counter": key_counter,
            "message_collector": message_collector,
            "price_collector": price_collector,
            "weather_collector": weather_collector,
            "log_collector": log_collector,
            "tracker_collector": tracker_collector,
            "kalshi_collector": kalshi_collector,
            "section_printer": section_printer,
            "service_printer": service_printer,
            "metrics_printer": metrics_printer,
        }

    @staticmethod
    def initialize_kalshi_state():
        """Initialize Kalshi client state."""
        return None, asyncio.Lock()

    @staticmethod
    def initialize_instance_attributes(instance, process_manager, health_checker, metadata_store, tracker_controller):
        """Initialize all instance attributes for OptimizedStatusReporter."""
        (
            instance.process_manager,
            instance.health_checker,
            instance.metadata_store,
            instance.tracker_controller,
        ) = (process_manager, health_checker, metadata_store, tracker_controller)
        instance._kalshi_client, instance._kalshi_client_lock = StatusReporterInitializer.initialize_kalshi_state()
        components = StatusReporterInitializer.initialize_components(
            process_manager,
            health_checker,
            metadata_store,
            tracker_controller,
            instance._emit_status_line,
        )
        for key, value in components.items():
            setattr(instance, f"_{key}", value)
