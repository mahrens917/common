"""Helper functions for create_status_report_coordinator factory."""

from dataclasses import dataclass

from ..basic_info_printer import BasicInfoPrinter as ConsoleSectionPrinter
from ..data_coercion import DataCoercion
from ..data_formatting import DataFormatting
from ..day_night_detector import DayNightDetector
from ..health_snapshot_collector import HealthSnapshotCollector
from ..kalshi_market_status_collector import KalshiMarketStatusCollector
from ..log_activity_collector import LogActivityCollector
from ..log_activity_formatter import LogActivityFormatter
from ..message_metrics_collector import MessageMetricsCollector
from ..moon_phase_calculator import MoonPhaseCalculator
from ..price_data_collector import PriceDataCollector
from ..process_resource_tracker import ProcessResourceTracker
from ..realtime_metrics_collector import RealtimeMetricsCollector
from ..redis_key_counter import RedisKeyCounter
from ..service_state_collector import ServiceStateCollector
from ..service_status_formatter import ServiceStatusFormatter
from ..status_report_coordinator import (
    StatusReportCoordinator,
    StatusReportCoordinatorCollectors,
    StatusReportCoordinatorConfig,
)
from ..tracker_status_collector import TrackerStatusCollector
from ..weather_section_generator import WeatherSectionGenerator
from ..weather_temperature_collector import WeatherTemperatureCollector


@dataclass(frozen=True)
class StatusReportCollectors:
    """All collectors for status report coordinator."""

    service_state_collector: ServiceStateCollector
    tracker_status_collector: TrackerStatusCollector
    health_snapshot_collector: HealthSnapshotCollector
    log_activity_collector: LogActivityCollector
    console_section_printer: ConsoleSectionPrinter
    weather_section_generator: WeatherSectionGenerator
    data_coercion: DataCoercion


def create_utility_components():
    """Create data coercion, formatting, and time utilities."""
    from ..time_formatter import TimeFormatter

    data_coercion = DataCoercion()
    data_formatting = DataFormatting()
    time_formatter = TimeFormatter()
    return data_coercion, data_formatting, time_formatter


def create_calculators():
    """Create moon phase calculator and day/night detector."""
    moon_phase_calculator = MoonPhaseCalculator()
    day_night_detector = DayNightDetector(moon_phase_calculator)
    day_night_detector.load_weather_station_coordinates()
    return day_night_detector


def create_non_redis_collectors(process_manager, health_checker, tracker_controller):
    """Create collectors that don't require Redis client."""
    service_state_collector = ServiceStateCollector(process_manager)
    tracker_status_collector = TrackerStatusCollector(process_manager, tracker_controller)
    health_snapshot_collector = HealthSnapshotCollector(health_checker)
    log_activity_collector = LogActivityCollector(process_manager)
    return (
        service_state_collector,
        tracker_status_collector,
        health_snapshot_collector,
        log_activity_collector,
    )


def create_formatters_and_printers(
    process_manager, data_coercion, data_formatting, time_formatter, day_night_detector
):
    """Create formatters, printers, and generators."""
    resource_tracker = ProcessResourceTracker(process_manager)
    log_activity_formatter = LogActivityFormatter(time_formatter)
    service_status_formatter = ServiceStatusFormatter(resource_tracker, log_activity_formatter)
    console_section_printer = ConsoleSectionPrinter(process_manager, service_status_formatter)
    weather_section_generator = WeatherSectionGenerator(day_night_detector, data_coercion)
    return console_section_printer, weather_section_generator


async def create_coordinator_with_redis(
    redis_client,
    process_manager,
    health_checker,
    metadata_store,
    tracker_controller,
    collectors: StatusReportCollectors,
):
    """Create coordinator with Redis-dependent collectors."""
    redis_key_counter = RedisKeyCounter(redis_client)
    price_data_collector = PriceDataCollector(redis_client)
    weather_temp_collector = WeatherTemperatureCollector(redis_client)
    realtime_metrics_collector = RealtimeMetricsCollector(redis_client)
    kalshi_market_status_collector = KalshiMarketStatusCollector(redis_client)
    message_metrics_collector = MessageMetricsCollector(realtime_metrics_collector, metadata_store)

    coordinator_collectors = StatusReportCoordinatorCollectors(
        redis_key_counter=redis_key_counter,
        price_data_collector=price_data_collector,
        weather_temp_collector=weather_temp_collector,
        realtime_metrics_collector=realtime_metrics_collector,
        message_metrics_collector=message_metrics_collector,
        service_state_collector=collectors.service_state_collector,
        tracker_status_collector=collectors.tracker_status_collector,
        health_snapshot_collector=collectors.health_snapshot_collector,
        log_activity_collector=collectors.log_activity_collector,
        kalshi_market_status_collector=kalshi_market_status_collector,
    )

    config = StatusReportCoordinatorConfig(
        process_manager=process_manager,
        health_checker=health_checker,
        metadata_store=metadata_store,
        tracker_controller=tracker_controller,
        collectors=coordinator_collectors,
        console_section_printer=collectors.console_section_printer,
        weather_section_generator=collectors.weather_section_generator,
        data_coercion=collectors.data_coercion,
    )

    return StatusReportCoordinator(config)
