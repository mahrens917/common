from __future__ import annotations

"""Helper for creating system metrics charts"""


import logging

from .chart_title_formatter import ChartTitleFormatter
from .system_metrics_collector import SystemMetricsCollector

logger = logging.getLogger("src.monitor.chart_generator")


class SystemChartCreator:
    """Creates system metrics charts for CPU and memory"""

    def __init__(
        self,
        *,
        primary_color: str,
        generate_unified_chart_func,
    ):
        self.primary_color = primary_color
        self.generate_unified_chart_func = generate_unified_chart_func
        self.metrics_collector = SystemMetricsCollector()
        self.title_formatter = ChartTitleFormatter()

    async def create_system_chart(self, metric_type: str, hours: int, redis_client) -> str:
        """Create a system metrics chart for CPU or memory"""
        timestamps, values = await self.metrics_collector.collect_system_metric_data(redis_client, metric_type, hours)

        chart_title = self.title_formatter.format_system_chart_title(metric_type)
        formatter = lambda x: f"{x:.1f}%"

        return await self.generate_unified_chart_func(
            timestamps=timestamps,
            values=values,
            chart_title=chart_title,
            y_label="",
            value_formatter_func=formatter,
            line_color=self.primary_color,
        )
