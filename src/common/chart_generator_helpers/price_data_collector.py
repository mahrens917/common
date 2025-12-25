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

            timestamps = []
            prices = []

            for timestamp_int, price_float in price_data:
                try:
                    dt = datetime.fromtimestamp(timestamp_int, tz=timezone.utc)
                    timestamps.append(dt)
                    prices.append(float(price_float))
                except (  # policy_guard: allow-silent-handler
                    ValueError,
                    TypeError,
                ):
                    logger.warning(f"Skipping invalid price data point for {symbol}: timestamp={timestamp_int}, price={price_float}, error")
                    continue

            if not timestamps or not prices:
                raise InsufficientDataError(f"No valid price data for {symbol}")

            sorted_data = sorted(zip(timestamps, prices))
            timestamps, prices = zip(*sorted_data)
            timestamps = list(timestamps)
            prices = list(prices)

            # Ensure we always display a full 24 hours of history before the forecast
            if timestamps:
                history_span = timestamps[-1] - timedelta(hours=24)
                first_timestamp = timestamps[0]
                if first_timestamp > history_span:
                    synthetic_time = history_span.replace(tzinfo=first_timestamp.tzinfo)
                    timestamps.insert(0, synthetic_time)
                    prices.insert(0, prices[0])

            return timestamps, prices

        finally:
            await price_tracker.cleanup()
