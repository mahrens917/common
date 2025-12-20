from __future__ import annotations

"""Helper for creating load monitoring charts"""


import logging

from .chart_title_formatter import ChartTitleFormatter
from .load_data_collector import LoadDataCollector

logger = logging.getLogger("src.monitor.chart_generator")


class LoadChartCreator:
    """Creates load monitoring charts for services"""

    def __init__(
        self,
        *,
        primary_color: str,
        generate_unified_chart_func,
    ):
        self.primary_color = primary_color
        self.generate_unified_chart_func = generate_unified_chart_func
        self.load_collector = LoadDataCollector()
        self.title_formatter = ChartTitleFormatter()

    async def create_load_chart(self, service_name: str, hours: int) -> str:
        """Create a load monitoring chart for a specific service"""
        timestamps, values = await self.load_collector.collect_service_load_data(service_name, hours)

        chart_title = self.title_formatter.format_load_chart_title(service_name)
        load_formatter = lambda x: f"{x:,.0f}"

        return await self.generate_unified_chart_func(
            timestamps=timestamps,
            values=values,
            chart_title=chart_title,
            y_label="",
            value_formatter_func=load_formatter,
            line_color=self.primary_color,
        )
