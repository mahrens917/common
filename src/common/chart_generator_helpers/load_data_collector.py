from __future__ import annotations

"""Helper for collecting load monitoring data from MetadataStore"""


import logging
from datetime import datetime
from typing import List, Tuple

from common.metadata_store import MetadataStore

from ..chart_generator.exceptions import InsufficientDataError

logger = logging.getLogger("src.monitor.chart_generator")

# Minimum data points required for meaningful chart
_MIN_DATA_POINTS = 2


class LoadDataCollector:
    """Collects load monitoring data from MetadataStore"""

    async def collect_service_load_data(self, service_name: str, hours: int) -> Tuple[List[datetime], List[float]]:
        """
        Collect load data for a service from MetadataStore

        Args:
            service_name: Name of service (deribit, kalshi)
            hours: Number of hours to fetch

        Returns:
            Tuple of (timestamps, values)

        Raises:
            InsufficientDataError: If no valid data available
        """
        metadata_store = MetadataStore()
        await metadata_store.initialize()

        try:
            history_data = await metadata_store.get_service_history(service_name, hours)

            if not history_data:
                raise InsufficientDataError(f"No history data available for {service_name}")

            timestamps = []
            values = []

            for entry in history_data:
                if "messages_per_minute" in entry:
                    value = entry["messages_per_minute"]
                elif "messages_per_second" in entry:
                    value = entry["messages_per_second"]
                else:
                    value = None

                if value is None:
                    continue

                try:
                    numeric_value = float(value)
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                if numeric_value > 0:
                    timestamps.append(entry["timestamp"])
                    values.append(numeric_value)

            if len(timestamps) < _MIN_DATA_POINTS:
                raise InsufficientDataError(f"Insufficient data points for {service_name}: {len(timestamps)}")

            return timestamps, values

        finally:
            await metadata_store.cleanup()
