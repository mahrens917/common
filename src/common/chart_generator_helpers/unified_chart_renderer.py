from __future__ import annotations

"""Helper for rendering unified charts with all features"""


import logging
from typing import TYPE_CHECKING

from .chart_data_preparer import ChartDataPreparer
from .chart_features_applier import ChartFeaturesApplier
from .chart_saver import ChartSaver
from .config import ChartComponentData, ChartPreparationData

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

logger = logging.getLogger("src.monitor.chart_generator")


class UnifiedChartRenderer:
    """Renders complete unified charts with all features"""

    def __init__(
        self,
        *,
        primary_color: str,
        secondary_color: str,
        highlight_color: str,
        dpi: float,
        background_color: str,
        configure_time_axis_func,
    ):
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.highlight_color = highlight_color
        self.dpi = dpi
        self.background_color = background_color
        self.configure_time_axis_func = configure_time_axis_func

    async def render_chart_and_save(self, *, fig: Figure, ax: Axes, **kwargs) -> str:
        """Render complete chart with all components and save to file"""
        data_preparer = ChartDataPreparer(
            primary_color=self.primary_color,
            secondary_color=self.secondary_color,
            highlight_color=self.highlight_color,
        )

        preparation_data = ChartPreparationData(
            ax=ax,
            timestamps=kwargs["timestamps"],
            values=kwargs["values"],
            prediction_timestamps=kwargs.get("prediction_timestamps"),
            prediction_values=kwargs.get("prediction_values"),
            prediction_uncertainties=kwargs.get("prediction_uncertainties"),
            station_coordinates=kwargs.get("station_coordinates"),
            is_temperature_chart=kwargs["is_temperature_chart"],
            is_price_chart=kwargs["is_price_chart"],
            is_pnl_chart=kwargs["is_pnl_chart"],
            line_color=kwargs.get("line_color"),
            value_formatter=kwargs.get("value_formatter"),
            mdates=kwargs["mdates"],
            np=kwargs["np"],
        )

        time_context, stats, overlay_result, _ = data_preparer.prepare_and_render_series(
            ax=ax,
            timestamps=kwargs["timestamps"],
            values=kwargs["values"],
            data=preparation_data,
        )

        component_data = ChartComponentData(
            ax=ax,
            values=kwargs["values"],
            stats=stats,
            time_context=time_context,
            overlay_result=overlay_result,
            prediction_values=kwargs.get("prediction_values"),
            prediction_uncertainties=kwargs.get("prediction_uncertainties"),
            vertical_lines=kwargs.get("vertical_lines") or [],
            dawn_dusk_periods=kwargs.get("dawn_dusk_periods") or [],
            is_pnl_chart=kwargs["is_pnl_chart"],
            is_price_chart=kwargs["is_price_chart"],
            is_temperature_chart=kwargs["is_temperature_chart"],
            kalshi_strikes=kwargs.get("kalshi_strikes"),
            chart_title=kwargs["chart_title"],
            y_label=kwargs["y_label"],
            station_icao=kwargs.get("station_icao"),
            value_formatter=kwargs.get("value_formatter"),
            add_kalshi_strike_lines_func=kwargs["add_kalshi_strike_lines_func"],
            add_comprehensive_temperature_labels_func=kwargs[
                "add_comprehensive_temperature_labels_func"
            ],
            mdates=kwargs["mdates"],
        )

        features_applier = ChartFeaturesApplier(
            configure_time_axis_func=self.configure_time_axis_func
        )
        await features_applier.apply_all_features(
            data=component_data,
            format_y_axis_func=kwargs["format_y_axis_func"],
            resolve_trade_visualizer_func=kwargs["resolve_trade_visualizer_func"],
            station_coordinates=kwargs.get("station_coordinates"),
        )

        fig.tight_layout()

        chart_saver = ChartSaver(dpi=self.dpi, background_color=self.background_color)
        return chart_saver.save_chart_figure(fig, kwargs["tempfile"], kwargs["plt"])
