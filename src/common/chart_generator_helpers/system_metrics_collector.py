from __future__ import annotations

"""Helper for collecting system metrics from Redis"""


import logging
import time
from datetime import datetime, timezone
from typing import List, Tuple

from common.redis_protocol.typing import RedisClient, ensure_awaitable

from ..chart_generator.exceptions import InsufficientDataError

logger = logging.getLogger("src.monitor.chart_generator")

# Minimum data points required for meaningful chart
_MIN_DATA_POINTS = 2


class SystemMetricsCollector:
    """Collects system metrics (CPU, memory) from Redis"""

    async def collect_system_metric_data(
        self, redis_client: RedisClient, metric_type: str, hours: int
    ) -> Tuple[List[datetime], List[float]]:
        """
        Collect system metric data from Redis

        Args:
            redis_client: Redis client
            metric_type: Type of metric (cpu, memory)
            hours: Number of hours to fetch

        Returns:
            Tuple of (timestamps, values)

        Raises:
            InsufficientDataError: If no valid data available
        """
        redis_key = f"history:{metric_type}"
        data = await ensure_awaitable(redis_client.hgetall(redis_key))

        if not data:
            raise InsufficientDataError(f"No history data available for {metric_type}")

        current_time = int(time.time())
        start_time = current_time - (hours * 3600)

        timestamps = []
        values = []

        for datetime_str, value_str in data.items():
            try:
                if isinstance(datetime_str, bytes):
                    datetime_str = datetime_str.decode()
                if isinstance(value_str, bytes):
                    value_str = value_str.decode()

                dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                timestamp = int(dt.timestamp())

                if timestamp >= start_time and float(value_str) > 0:
                    dt_obj = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    timestamps.append(dt_obj)
                    values.append(float(value_str))

            except (
                UnicodeDecodeError,
                ValueError,
                TypeError,
            ):
                logger.warning(f"Skipping invalid {metric_type} data point: {datetime_str}={value_str}, error")
                continue

        if len(timestamps) < _MIN_DATA_POINTS:
            raise InsufficientDataError(f"Insufficient data points for {metric_type}: {len(timestamps)}")

        sorted_data = sorted(zip(timestamps, values))
        timestamps, values = zip(*sorted_data)
        return list(timestamps), list(values)
