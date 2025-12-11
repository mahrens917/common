"""
Status reporter helpers - focused components for status reporting.

This package contains all helper classes extracted from OptimizedStatusReporter:
- Data collection helpers
- Data conversion/coercion helpers
- Formatting helpers
- Console output helpers
"""

from .basic_info_printer import BasicInfoPrinter as ConsoleSectionPrinter
from .data_coercion import DataCoercion
from .data_formatting import DataFormatting
from .day_night_detector import DayNightDetector
from .health_snapshot_collector import HealthSnapshotCollector
from .initialization import StatusReporterInitializer
from .kalshi_market_status_collector import KalshiMarketStatusCollector
from .log_activity_collector import LogActivityCollector
from .log_activity_formatter import LogActivityFormatter
from .message_metrics_collector import MessageMetricsCollector
from .moon_phase_calculator import MoonPhaseCalculator
from .price_data_collector import PriceDataCollector
from .process_resource_tracker import ProcessResourceTracker
from .realtime_metrics_collector import RealtimeMetricsCollector
from .redis_key_counter import RedisKeyCounter
from .service_state_collector import ServiceStateCollector
from .service_status_formatter import ServiceStatusFormatter
from .status_report_coordinator import (
    StatusReportCoordinator,
    StatusReportCoordinatorCollectors,
    StatusReportCoordinatorConfig,
)
from .time_formatter import TimeFormatter
from .tracker_status_collector import TrackerStatusCollector
from .weather_section_generator import WeatherSectionGenerator
from .weather_temperature_collector import WeatherTemperatureCollector

__all__ = [
    "ConsoleSectionPrinter",
    "DataCoercion",
    "DataFormatting",
    "DayNightDetector",
    "HealthSnapshotCollector",
    "KalshiMarketStatusCollector",
    "LogActivityCollector",
    "LogActivityFormatter",
    "MessageMetricsCollector",
    "MoonPhaseCalculator",
    "PriceDataCollector",
    "ProcessResourceTracker",
    "RealtimeMetricsCollector",
    "RedisKeyCounter",
    "ServiceStateCollector",
    "ServiceStatusFormatter",
    "StatusReportCoordinator",
    "StatusReporterInitializer",
    "TimeFormatter",
    "TrackerStatusCollector",
    "WeatherSectionGenerator",
    "WeatherTemperatureCollector",
]


def create_status_report_coordinator(process_manager, health_checker, metadata_store, tracker_controller):
    """
    Factory function to create StatusReportCoordinator with all dependencies.
    """
    utilities = _build_status_report_utilities(process_manager)
    non_redis_collectors = _build_non_redis_collectors(process_manager, tracker_controller, health_checker)

    async def _create_with_redis_client(redis_client):
        redis_collectors = _build_redis_collectors(redis_client, metadata_store)
        return _assemble_status_report_coordinator(
            process_manager,
            health_checker,
            metadata_store,
            tracker_controller,
            utilities,
            non_redis_collectors,
            redis_collectors,
        )

    return _create_with_redis_client


def _build_status_report_utilities(process_manager):
    data_coercion = DataCoercion()
    time_formatter = TimeFormatter()
    moon_phase_calculator = MoonPhaseCalculator()
    day_night_detector = DayNightDetector(moon_phase_calculator)
    day_night_detector.load_weather_station_coordinates()
    resource_tracker = ProcessResourceTracker(process_manager)
    log_activity_formatter = LogActivityFormatter(time_formatter)
    service_status_formatter = ServiceStatusFormatter(resource_tracker, log_activity_formatter)
    console_section_printer = ConsoleSectionPrinter(process_manager, service_status_formatter)
    weather_section_generator = WeatherSectionGenerator(day_night_detector, data_coercion)
    return {
        "data_coercion": data_coercion,
        "console_section_printer": console_section_printer,
        "weather_section_generator": weather_section_generator,
    }


def _build_non_redis_collectors(process_manager, tracker_controller, health_checker):
    service_state_collector = ServiceStateCollector(process_manager)
    tracker_status_collector = TrackerStatusCollector(process_manager, tracker_controller)
    health_snapshot_collector = HealthSnapshotCollector(health_checker)
    log_activity_collector = LogActivityCollector(process_manager)
    return {
        "service_state_collector": service_state_collector,
        "tracker_status_collector": tracker_status_collector,
        "health_snapshot_collector": health_snapshot_collector,
        "log_activity_collector": log_activity_collector,
    }


def _build_redis_collectors(redis_client, metadata_store):
    redis_key_counter = RedisKeyCounter(redis_client)
    price_data_collector = PriceDataCollector(redis_client)
    weather_temp_collector = WeatherTemperatureCollector(redis_client)
    realtime_metrics_collector = RealtimeMetricsCollector(redis_client)
    kalshi_market_status_collector = KalshiMarketStatusCollector(redis_client)
    message_metrics_collector = MessageMetricsCollector(realtime_metrics_collector, metadata_store)
    return {
        "redis_key_counter": redis_key_counter,
        "price_data_collector": price_data_collector,
        "weather_temp_collector": weather_temp_collector,
        "realtime_metrics_collector": realtime_metrics_collector,
        "kalshi_market_status_collector": kalshi_market_status_collector,
        "message_metrics_collector": message_metrics_collector,
    }


def _assemble_status_report_coordinator(
    process_manager,
    health_checker,
    metadata_store,
    tracker_controller,
    utilities,
    non_redis_collectors,
    redis_collectors,
):
    collectors = StatusReportCoordinatorCollectors(
        redis_key_counter=redis_collectors["redis_key_counter"],
        price_data_collector=redis_collectors["price_data_collector"],
        weather_temp_collector=redis_collectors["weather_temp_collector"],
        realtime_metrics_collector=redis_collectors["realtime_metrics_collector"],
        message_metrics_collector=redis_collectors["message_metrics_collector"],
        service_state_collector=non_redis_collectors["service_state_collector"],
        tracker_status_collector=non_redis_collectors["tracker_status_collector"],
        health_snapshot_collector=non_redis_collectors["health_snapshot_collector"],
        log_activity_collector=non_redis_collectors["log_activity_collector"],
        kalshi_market_status_collector=redis_collectors["kalshi_market_status_collector"],
    )
    config = StatusReportCoordinatorConfig(
        process_manager=process_manager,
        health_checker=health_checker,
        metadata_store=metadata_store,
        tracker_controller=tracker_controller,
        collectors=collectors,
        console_section_printer=utilities["console_section_printer"],
        weather_section_generator=utilities["weather_section_generator"],
        data_coercion=utilities["data_coercion"],
    )
    return StatusReportCoordinator(config)
