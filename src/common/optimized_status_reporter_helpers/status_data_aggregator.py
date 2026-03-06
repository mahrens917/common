"""
Status data aggregation coordinator for OptimizedStatusReporter.

Extracted from OptimizedStatusReporter to reduce class size.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional

from common.kalshi_api.client import KalshiClient


@dataclass(frozen=True)
class StatusDataCollectors:
    """All collectors for status data aggregation."""

    service_collector: Any
    health_collector: Any
    key_counter: Any
    message_collector: Any
    price_collector: Any
    weather_collector: Any
    log_collector: Any
    tracker_collector: Any
    kalshi_collector: Any


class StatusDataAggregator:
    """Coordinates data collection from multiple collectors."""

    def __init__(self, collectors: StatusDataCollectors):
        """Initialize aggregator with all collectors."""
        self._service_collector = collectors.service_collector
        self._health_collector = collectors.health_collector
        self._key_counter = collectors.key_counter
        self._message_collector = collectors.message_collector
        self._price_collector = collectors.price_collector
        self._weather_collector = collectors.weather_collector
        self._log_collector = collectors.log_collector
        self._tracker_collector = collectors.tracker_collector
        self._kalshi_collector = collectors.kalshi_collector

    async def gather_status_data(self, redis_client, process_monitor, kalshi_client: KalshiClient) -> Dict[str, Any]:
        """Gather all status data using collectors."""
        running_services, redis_pid, health_snapshot = await asyncio.gather(
            self._service_collector.collect_running_services(),
            self._resolve_redis_pid(process_monitor),
            self._health_collector.collect_health_snapshot(),
        )

        # Set redis_client on collectors that need it
        self._key_counter.redis_client = redis_client
        self._message_collector.redis_client = redis_client
        self._message_collector.realtime_collector.redis_client = redis_client
        self._price_collector.redis_client = redis_client
        self._weather_collector.redis_client = redis_client
        self._kalshi_collector.redis_client = redis_client

        key_counts, message_metrics, price_data, weather_temps, kalshi_status, (log_activity_map, stale_logs), tracker_status = (
            await asyncio.gather(
                self._key_counter.collect_key_counts(),
                self._message_collector.collect_message_metrics(),
                self._price_collector.collect_price_data(),
                self._weather_collector.collect_weather_temperatures(),
                self._kalshi_collector.get_kalshi_market_status(),
                self._log_collector.collect_log_activity_map(),
                self._tracker_collector.collect_tracker_status(),
            )
        )
        running_services = self._tracker_collector.merge_tracker_service_state(running_services, tracker_status)

        return {
            "redis_process": {"pid": redis_pid},
            "running_services": running_services,
            "redis_connection_healthy": health_snapshot["redis_connection_healthy"],
            **key_counts,
            **message_metrics,
            "weather_temperatures": weather_temps,
            "stale_logs": stale_logs,
            "log_activity": log_activity_map,
            **health_snapshot,
            **price_data,
            "kalshi_market_status": kalshi_status,
            "tracker_status": tracker_status,
        }

    async def _resolve_redis_pid(self, process_monitor) -> Optional[int]:
        """Get Redis process PID."""
        redis_processes = await process_monitor.get_redis_processes()
        return redis_processes[0].pid if redis_processes else None
