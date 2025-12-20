from __future__ import annotations

"""Helper for building chart time contexts"""


import logging
from datetime import datetime
from typing import List, Optional, Tuple

from src.common.chart_components import (
    build_axis_timestamps,
    ensure_naive_timestamps,
    localize_temperature_timestamps,
)
from src.common.chart_generator.contexts import ChartTimeContext

logger = logging.getLogger("src.monitor.chart_generator")


class TimeContextBuilder:
    """Builds time context for chart rendering"""

    def prepare_time_context(
        self,
        *,
        timestamps: List[datetime],
        prediction_timestamps: Optional[List[datetime]],
        station_coordinates: Optional[Tuple[float, float]],
        is_temperature_chart: bool,
    ) -> ChartTimeContext:
        """Build complete time context with timezone handling"""
        timestamps_naive = ensure_naive_timestamps(timestamps)
        prediction_naive = (
            ensure_naive_timestamps(prediction_timestamps) if prediction_timestamps else None
        )
        axis_timestamps = build_axis_timestamps(timestamps_naive, prediction_naive)
        localized_result = (
            localize_temperature_timestamps(timestamps_naive, station_coordinates)
            if is_temperature_chart and station_coordinates
            else None
        )
        localized = localized_result.timestamps if localized_result else None
        local_timezone = localized_result.timezone if localized_result else None
        plot_timestamps = localized if (is_temperature_chart and localized) else timestamps_naive

        return ChartTimeContext(
            naive=list(timestamps_naive),
            prediction=list(prediction_naive) if prediction_naive else None,
            axis=list(axis_timestamps),
            localized=localized,
            local_timezone=local_timezone,
            plot=list(plot_timestamps),
        )
