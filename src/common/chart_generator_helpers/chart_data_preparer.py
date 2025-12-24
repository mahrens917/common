from __future__ import annotations

"""Helper for preparing chart data before rendering"""


import logging
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional, Tuple

from common.chart_components import (
    PredictionOverlayParams,
    render_prediction_overlay_if_needed,
)

from .config import ChartPreparationData, PrimarySeriesRenderConfig
from .latest_value_annotator import LatestValueAnnotator
from .primary_series_renderer import PrimarySeriesRenderer
from .series_statistics_calculator import SeriesStatisticsCalculator
from .time_context_builder import TimeContextBuilder

if TYPE_CHECKING:
    from matplotlib.axes import Axes

    from common.chart_components import PredictionOverlayResult
    from common.chart_generator.contexts import ChartStatistics, ChartTimeContext

logger = logging.getLogger("src.monitor.chart_generator")


class ChartDataPreparer:
    """Prepares chart data and renders initial series"""

    def __init__(self, *, primary_color: str, secondary_color: str, highlight_color: str):
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.highlight_color = highlight_color

    def prepare_and_render_series(
        self,
        *,
        ax: Axes,
        timestamps: List[datetime],
        values: List[float],
        data: ChartPreparationData,
    ) -> tuple[ChartTimeContext, ChartStatistics, PredictionOverlayResult, Optional[Tuple[datetime, float]]]:
        """Prepare chart data and render primary series"""
        time_context_builder = TimeContextBuilder()
        stats_calculator = SeriesStatisticsCalculator()

        time_context = time_context_builder.prepare_time_context(
            timestamps=timestamps,
            prediction_timestamps=data.prediction_timestamps,
            station_coordinates=data.station_coordinates,
            is_temperature_chart=data.is_temperature_chart,
        )
        stats = stats_calculator.compute_series_statistics(values, data.np)
        plot_color = data.line_color if data.line_color is not None else self.primary_color

        series_renderer = PrimarySeriesRenderer(primary_color=self.primary_color, secondary_color=self.secondary_color)
        render_config = PrimarySeriesRenderConfig(
            ax=ax,
            values=values,
            plot_color=plot_color,
            stats=stats,
            time_context=time_context,
            is_temperature_chart=data.is_temperature_chart,
            is_pnl_chart=data.is_pnl_chart,
            is_price_chart=data.is_price_chart,
            mdates=data.mdates,
        )
        latest_point = series_renderer.render_primary_series(config=render_config)

        overlay_params = PredictionOverlayParams(
            historical_naive=time_context.naive,
            historical_values=values,
            precomputed_prediction=time_context.prediction,
            prediction_timestamps=data.prediction_timestamps,
            prediction_values=data.prediction_values,
            prediction_uncertainties=data.prediction_uncertainties,
            plot_color=plot_color,
        )
        overlay_result = render_prediction_overlay_if_needed(
            ax=ax,
            params=overlay_params,
        )

        self._annotate_latest_if_applicable(
            ax=ax,
            latest_point=latest_point,
            formatter=data.value_formatter,
            is_pnl_chart=data.is_pnl_chart,
            mdates=data.mdates,
        )

        return time_context, stats, overlay_result, latest_point

    def _annotate_latest_if_applicable(
        self,
        *,
        ax: Axes,
        latest_point: Optional[Tuple[datetime, float]],
        formatter,
        is_pnl_chart: bool,
        mdates,
    ) -> None:
        """Annotate latest value if applicable"""
        if latest_point is None or is_pnl_chart:
            return
        annotator = LatestValueAnnotator(
            primary_color=self.primary_color,
            highlight_color=self.highlight_color,
        )
        annotator.annotate_latest_value(
            ax=ax,
            timestamp=latest_point[0],
            value=latest_point[1],
            formatter=formatter,
            mdates=mdates,
        )
