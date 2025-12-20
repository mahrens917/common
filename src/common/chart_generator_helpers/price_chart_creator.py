from __future__ import annotations

"""Helper for creating price charts with predictions"""


import logging
from datetime import datetime, timezone
from typing import Optional

from src.common.price_path_calculator import PricePathComputationError

from .chart_title_formatter import ChartTitleFormatter
from .price_data_collector import PriceDataCollector
from .progress_notifier import ProgressNotifier

logger = logging.getLogger("src.monitor.chart_generator")


class PriceChartCreator:
    """Creates price charts with predicted price paths"""

    def __init__(
        self,
        *,
        primary_color: str,
        price_path_calculator,
        price_path_horizon_days: int,
        progress_notifier: ProgressNotifier,
        generate_unified_chart_func,
    ):
        self.primary_color = primary_color
        self.price_path_calculator = price_path_calculator
        self.price_path_horizon_days = price_path_horizon_days
        self.progress_notifier = progress_notifier
        self.generate_unified_chart_func = generate_unified_chart_func
        self.price_collector = PriceDataCollector()
        self.title_formatter = ChartTitleFormatter()

    async def create_price_chart(self, symbol: str, prediction_horizon_days: Optional[int] = None) -> str:
        """Create a price chart for BTC or ETH with predicted path"""
        self.progress_notifier.notify_progress(f"{symbol}: fetching price history")
        timestamps, prices = await self.price_collector.collect_price_history(symbol)

        horizon_days = prediction_horizon_days or self.price_path_horizon_days
        self.progress_notifier.notify_progress(f"{symbol}: computing price path ({horizon_days}d)")
        predicted_path = self.price_path_calculator.generate_price_path(symbol, prediction_horizon_days=horizon_days)
        if not predicted_path:
            raise PricePathComputationError(f"Price path calculator returned no points for {symbol}")

        predicted_timestamps = [datetime.fromtimestamp(point[0], tz=timezone.utc) for point in predicted_path]
        predicted_prices = [point[1] for point in predicted_path]
        predicted_uncertainties = [point[2] for point in predicted_path]

        current_price = prices[-1]
        chart_title = self.title_formatter.format_price_chart_title(symbol, current_price)

        price_formatter = lambda x: f"${x:,.0f}" if x == int(x) else f"${x:,.2f}"

        current_time = datetime.now(timezone.utc)

        self.progress_notifier.notify_progress(f"{symbol}: rendering chart")
        return await self.generate_unified_chart_func(
            timestamps=timestamps,
            values=prices,
            chart_title=chart_title,
            y_label="",
            value_formatter_func=price_formatter,
            is_price_chart=True,
            prediction_timestamps=predicted_timestamps,
            prediction_values=predicted_prices,
            prediction_uncertainties=predicted_uncertainties,
            vertical_lines=[(current_time, "black", "Current Time")],
            line_color=self.primary_color,
        )
