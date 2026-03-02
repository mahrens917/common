from __future__ import annotations

"""Helper for collecting price history data"""


import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from common.history_tracker import PriceHistoryTracker

from ..chart_generator.exceptions import InsufficientDataError

logger = logging.getLogger("src.monitor.chart_generator")

# Minimum data points required for meaningful chart
_MIN_DATA_POINTS = 2


class PriceDataCollector:
    """Collects price history data for BTC/ETH"""

    async def collect_price_history(self, symbol: str) -> Tuple[List[datetime], List[float]]:
        """
        Collect price history for a symbol

        Args:
            symbol: Symbol to collect (BTC, ETH)

        Returns:
            Tuple of (timestamps, prices)

        Raises:
            InsufficientDataError: If no valid data available
        """
        cg_module = sys.modules.get("src.monitor.chart_generator")
        tracker_cls = getattr(cg_module, "PriceHistoryTracker", PriceHistoryTracker)
        price_tracker = tracker_cls()

        try:
            await price_tracker.initialize()
            price_data = await price_tracker.get_price_history(symbol)

            if not price_data:
                raise InsufficientDataError(f"No price data available for {symbol}")

            if len(price_data) < _MIN_DATA_POINTS:
                raise InsufficientDataError(f"Insufficient price data for {symbol}: {len(price_data)} points")

            data_points: List[Tuple[datetime, float]] = []

            for timestamp_int, price_float in price_data:
                try:
                    dt = datetime.fromtimestamp(timestamp_int, tz=timezone.utc)
                    data_points.append((dt, float(price_float)))
                except (  # policy_guard: allow-silent-handler
                    ValueError,
                    TypeError,
                ):
                    logger.warning(f"Skipping invalid price data point for {symbol}: timestamp={timestamp_int}, price={price_float}, error")
                    continue

            if not data_points:
                raise InsufficientDataError(f"No valid price data for {symbol}")

            data_points.sort()
            timestamps, prices = (list(col) for col in zip(*data_points))
            self._pad_to_24h(timestamps, prices)
            return timestamps, prices

        finally:
            await price_tracker.cleanup()

    @staticmethod
    def _pad_to_24h(timestamps: List[datetime], prices: List[float]) -> None:
        """Ensure at least 24 hours of history by prepending a synthetic point if needed."""
        if not timestamps:
            return
        history_span = timestamps[-1] - timedelta(hours=24)
        if timestamps[0] > history_span:
            synthetic_time = history_span.replace(tzinfo=timestamps[0].tzinfo)
            timestamps.insert(0, synthetic_time)
            prices.insert(0, prices[0])
