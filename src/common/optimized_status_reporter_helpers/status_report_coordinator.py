"""
Status report coordinator - slim orchestrator for status reporting.

Coordinates data collection and console output using focused helpers.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict

from redis.exceptions import RedisError

from common.redis_utils import RedisOperationError
from common.time_utils import get_current_utc
from common.truthy import pick_truthy

logger = logging.getLogger(__name__)

STATUS_REPORT_ERRORS = (
    RedisError,
    RedisOperationError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
    ValueError,
    ImportError,
)


@dataclass(frozen=True)
class DataGathererCollectors:
    """All collectors for DataGatherer."""

    redis_key_counter: Any
    price_data_collector: Any
    weather_temp_collector: Any
    message_metrics_collector: Any
    service_state_collector: Any
    tracker_status_collector: Any
    health_snapshot_collector: Any
    log_activity_collector: Any
    kalshi_market_status_collector: Any


@dataclass(frozen=True)
class StatusDictData:
    """Data for building status dictionary."""

    redis_pid: Any
    running_services: Any
    health_snapshot: Dict[str, Any]
    key_counts: Dict[str, Any]
    message_metrics: Dict[str, Any]
    price_data: Dict[str, Any]
    weather_temperatures: Any
    kalshi_market_status: Any
    log_activity_map: Any
    stale_logs: Any
    tracker_status: Any


@dataclass(frozen=True)
class StatusReportCoordinatorCollectors:
    """Collectors for StatusReportCoordinator."""

    redis_key_counter: Any
    price_data_collector: Any
    weather_temp_collector: Any
    realtime_metrics_collector: Any
    message_metrics_collector: Any
    service_state_collector: Any
    tracker_status_collector: Any
    health_snapshot_collector: Any
    log_activity_collector: Any
    kalshi_market_status_collector: Any


@dataclass(frozen=True)
class StatusReportCoordinatorConfig:
    """Configuration for StatusReportCoordinator."""

    process_manager: Any
    health_checker: Any
    metadata_store: Any
    tracker_controller: Any
    collectors: StatusReportCoordinatorCollectors
    console_section_printer: Any
    weather_section_generator: Any
    data_coercion: Any


class DataGatherer:
    """Collects all status data from various sources."""

    def __init__(self, collectors: DataGathererCollectors):
        self.redis_key_counter = collectors.redis_key_counter
        self.price_data_collector = collectors.price_data_collector
        self.weather_temp_collector = collectors.weather_temp_collector
        self.message_metrics_collector = collectors.message_metrics_collector
        self.service_state_collector = collectors.service_state_collector
        self.tracker_status_collector = collectors.tracker_status_collector
        self.health_snapshot_collector = collectors.health_snapshot_collector
        self.log_activity_collector = collectors.log_activity_collector
        self.kalshi_market_status_collector = collectors.kalshi_market_status_collector

    async def gather_all_status_data(self, redis_client) -> Dict[str, Any]:
        from common.process_monitor import get_global_process_monitor

        process_monitor = await get_global_process_monitor()
        running_services = await self.service_state_collector.collect_running_services()
        redis_pid = await self.service_state_collector.resolve_redis_pid(process_monitor)
        health_snapshot = await self.health_snapshot_collector.collect_health_snapshot()
        key_counts = await self.redis_key_counter.collect_key_counts()
        message_metrics = await self.message_metrics_collector.collect_message_metrics()
        price_data = await self.price_data_collector.collect_price_data()
        weather_temperatures = await self.weather_temp_collector.collect_weather_temperatures()
        kalshi_market_status = await self.kalshi_market_status_collector.get_kalshi_market_status()
        log_activity_map, stale_logs = await self.log_activity_collector.collect_log_activity_map()
        tracker_status = await self.tracker_status_collector.collect_tracker_status()
        running_services = self.tracker_status_collector.merge_tracker_service_state(running_services, tracker_status)
        data = StatusDictData(
            redis_pid=redis_pid,
            running_services=running_services,
            health_snapshot=health_snapshot,
            key_counts=key_counts,
            message_metrics=message_metrics,
            price_data=price_data,
            weather_temperatures=weather_temperatures,
            kalshi_market_status=kalshi_market_status,
            log_activity_map=log_activity_map,
            stale_logs=stale_logs,
            tracker_status=tracker_status,
        )
        return _build_status_dict(data)


def _build_status_dict(data: StatusDictData) -> Dict[str, Any]:
    return {
        "redis_process": {"pid": data.redis_pid},
        "running_services": data.running_services,
        "redis_connection_healthy": data.health_snapshot["redis_connection_healthy"],
        "redis_deribit_keys": data.key_counts["redis_deribit_keys"],
        "redis_kalshi_keys": data.key_counts["redis_kalshi_keys"],
        "redis_cfb_keys": data.key_counts["redis_cfb_keys"],
        "redis_weather_keys": data.key_counts["redis_weather_keys"],
        "deribit_messages_60s": data.message_metrics["deribit_messages_60s"],
        "kalshi_messages_60s": data.message_metrics["kalshi_messages_60s"],
        "cfb_messages_60s": data.message_metrics["cfb_messages_60s"],
        "asos_messages_65m": data.message_metrics["asos_messages_65m"],
        "weather_temperatures": data.weather_temperatures,
        "stale_logs": data.stale_logs,
        "log_activity": data.log_activity_map,
        "health_checks": data.health_snapshot["health_checks"],
        "system_resources_health": data.health_snapshot["system_resources_health"],
        "redis_health_check": data.health_snapshot["redis_health_check"],
        "ldm_listener_health": data.health_snapshot["ldm_listener_health"],
        "btc_price": data.price_data["btc_price"],
        "eth_price": data.price_data["eth_price"],
        "kalshi_market_status": data.kalshi_market_status,
        "tracker_status": data.tracker_status,
    }


class ConsolePrinter:
    """Prints status data to console in formatted sections."""

    def __init__(self, console_section_printer, weather_section_generator, data_coercion):
        self.console_section_printer = console_section_printer
        self.weather_section_generator = weather_section_generator
        self.data_coercion = data_coercion

    async def print_full_status(self, status_data: Dict[str, Any]):
        current_time = get_current_utc().strftime("%Y-%m-%d %H:%M:%S")
        self.console_section_printer._emit_status_line("=" * 60)
        kalshi_status = self.data_coercion.coerce_mapping(status_data.get("kalshi_market_status"))
        self.console_section_printer.print_exchange_info(current_time, kalshi_status)
        self.console_section_printer._emit_status_line()
        self.console_section_printer.print_price_info(status_data.get("btc_price"), status_data.get("eth_price"))
        self._print_weather_section(status_data)
        self._print_system_update_section(status_data)
        self._print_metrics_sections(status_data)

    def _print_weather_section(self, status_data: Dict[str, Any]):
        weather_temperatures = self.data_coercion.coerce_mapping(status_data.get("weather_temperatures"))
        weather_lines = self.weather_section_generator.generate_weather_section(weather_temperatures)
        self.console_section_printer.print_weather_section(weather_lines)

    def _print_system_update_section(self, status_data: Dict[str, Any]):
        self.console_section_printer._emit_status_line()
        self.console_section_printer._emit_status_line("📝 System Update:")
        tracker_status = self.data_coercion.coerce_mapping(status_data.get("tracker_status"))
        log_activity_map = pick_truthy(status_data.get("log_activity"), {})
        healthy_count, total_count = self.console_section_printer.print_managed_services(tracker_status, log_activity_map)
        self.console_section_printer.print_monitor_service(log_activity_map)
        self.console_section_printer._emit_status_line(f"📊 Process Summary: {healthy_count}/{total_count} running")

    def _print_metrics_sections(self, status_data: Dict[str, Any]):
        tracker_status = self.data_coercion.coerce_mapping(status_data.get("tracker_status"))
        self.console_section_printer.print_redis_health_section(status_data)
        self.console_section_printer.print_system_resources_section(status_data["system_resources_health"])
        self.console_section_printer.print_message_metrics_section(status_data)
        self.console_section_printer.print_weather_metrics_section(status_data)
        self.console_section_printer.print_tracker_status_section(tracker_status)


class StatusReportCoordinator:
    """Slim coordinator that delegates to focused helpers."""

    def __init__(self, config: StatusReportCoordinatorConfig):
        self.process_manager = config.process_manager
        self.health_checker = config.health_checker
        self.metadata_store = config.metadata_store
        self.tracker_controller = config.tracker_controller
        gatherer_collectors = DataGathererCollectors(
            redis_key_counter=config.collectors.redis_key_counter,
            price_data_collector=config.collectors.price_data_collector,
            weather_temp_collector=config.collectors.weather_temp_collector,
            message_metrics_collector=config.collectors.message_metrics_collector,
            service_state_collector=config.collectors.service_state_collector,
            tracker_status_collector=config.collectors.tracker_status_collector,
            health_snapshot_collector=config.collectors.health_snapshot_collector,
            log_activity_collector=config.collectors.log_activity_collector,
            kalshi_market_status_collector=config.collectors.kalshi_market_status_collector,
        )
        self.data_gatherer = DataGatherer(gatherer_collectors)
        self.console_printer = ConsolePrinter(config.console_section_printer, config.weather_section_generator, config.data_coercion)

    async def generate_and_stream_status_report(self) -> Dict[str, Any]:
        from common.redis_protocol.connection_pool_core import get_redis_client

        try:
            redis_client = await get_redis_client()
            status_data = await self.data_gatherer.gather_all_status_data(redis_client)
            await self.console_printer.print_full_status(status_data)
        except STATUS_REPORT_ERRORS as exc:
            logger.exception("Status report failed: %s", type(exc).__name__)
            raise RuntimeError("Status report generation failed") from exc
        else:
            return status_data
