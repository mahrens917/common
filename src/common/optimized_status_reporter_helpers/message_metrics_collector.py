"""
Message metrics aggregation from multiple sources.

Combines realtime metrics (Deribit, Kalshi) with metadata metrics (CFB, ASOS, METAR).
"""

import asyncio
import logging
from typing import Dict

from redis.exceptions import RedisError

from common.exceptions import DataError
from common.redis_utils import RedisOperationError

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


# Constants
_CONST_3 = 3


class MessageMetricsCollector:
    """Aggregates message metrics from Redis and metadata store."""

    def __init__(self, realtime_collector, metadata_store):
        self.realtime_collector = realtime_collector
        self.metadata_store = metadata_store

    async def collect_message_metrics(self) -> Dict[str, int]:
        """Collect all message metrics."""
        realtime_tasks = [
            self.realtime_collector.get_deribit_sum_last_60_seconds(),
            self.realtime_collector.get_kalshi_sum_last_60_seconds(),
        ]
        metadata_tasks = [self.metadata_store.get_service_metadata(name) for name in ["cfb", "asos", "metar"]]

        try:
            deribit_messages_60s, kalshi_messages_60s = await asyncio.gather(*realtime_tasks)
        except STATUS_REPORT_ERRORS as exc:  # policy_guard: allow-silent-handler
            raise RuntimeError("Failed to collect realtime message metrics") from exc

        try:
            metadata_results = await asyncio.gather(*metadata_tasks)
        except STATUS_REPORT_ERRORS as exc:  # policy_guard: allow-silent-handler
            raise DataError("Failed to collect metadata message metrics") from exc

        if len(metadata_results) != _CONST_3:
            raise DataError(f"Expected metadata for ['cfb', 'asos', 'metar'], got {len(metadata_results)} entries")

        cfb_messages = self._require_metadata_value("cfb", metadata_results[0], "messages_last_minute")
        asos_messages = self._require_metadata_value("asos", metadata_results[1], "messages_last_65_minutes")
        metar_messages = self._require_metadata_value("metar", metadata_results[2], "messages_last_65_minutes")

        return {
            "deribit_messages_60s": deribit_messages_60s,
            "kalshi_messages_60s": kalshi_messages_60s,
            "cfb_messages_60s": cfb_messages,
            "asos_messages_65m": asos_messages,
            "metar_messages_65m": metar_messages,
        }

    @staticmethod
    def _require_metadata_value(name: str, result: object, attribute: str) -> int:
        """Extract and validate metadata attribute value."""
        if result is None:
            raise DataError(f"Metadata for {name} service is unavailable")
        try:
            value = getattr(result, attribute)
        except AttributeError as exc:  # policy_guard: allow-silent-handler
            raise DataError(f"Metadata for {name} missing required attribute '{attribute}'") from exc
        if value is None:
            raise DataError(f"Metadata for {name} has null value for '{attribute}'")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
            raise DataError(f"Metadata for {name} contains non-numeric value for '{attribute}': {value}") from exc
