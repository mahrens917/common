from __future__ import annotations

import asyncio
import inspect
import logging
import os
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Sequence, Tuple

from src.common.chart_generator_helpers.pnl_breakdown_chart_renderer import (
    PnlBreakdownChartRenderer,
)

from ..dependencies import np, plt, tempfile
from ..exceptions import InsufficientDataError
from .base import UnifiedChartRendererMixin

logger = logging.getLogger("src.monitor.chart_generator")


class PnlChartRendererMixin(UnifiedChartRendererMixin):
    """Helper mixin for generating monitor P&L charts."""

    chart_width_inches: float
    chart_height_inches: float
    dpi: float
    background_color: str
    primary_color: str
    secondary_color: str
    highlight_color: str

    async def generate_pnl_charts(self, pnl_data: Dict[str, Any]) -> List[str]:
        """Delegate to the helper responsible for generating P&L charts."""
        return await self._generate_pnl_charts_impl(pnl_data)

    async def _generate_pnl_charts_impl(self: "PnlChartRendererMixin", pnl_data: Dict[str, Any]) -> List[str]:
        if not pnl_data:
            raise InsufficientDataError("No P&L data available for chart generation")

        chart_paths: List[str] = []
        chart_specs = (
            ("daily_pnl", self._generate_daily_pnl_chart),
            ("daily_pnl_dollars", self._generate_cumulative_pnl_chart),
            ("station_breakdown", self._generate_station_breakdown_chart),
            ("rule_breakdown", self._generate_rule_breakdown_chart),
        )

        try:
            for key, generator in chart_specs:
                dataset = pnl_data.get(key)
                if not dataset:
                    continue
                chart_paths.append(await _render_chart(self, generator, dataset))
        except asyncio.CancelledError:
            _cleanup_partial_charts(chart_paths)
            raise
        except (IOError, OSError, ValueError, RuntimeError):
            _cleanup_partial_charts(chart_paths)
            raise

        if not chart_paths:
            raise InsufficientDataError("No valid P&L data available for any chart type")
        return chart_paths

    async def _generate_daily_pnl_chart(self, daily_pnl_data: List[Tuple[date, float]]) -> str:
        """Delegate to the helper that renders the daily P&L chart."""
        return await _generate_daily_pnl_chart_impl(self, daily_pnl_data)

    async def _generate_cumulative_pnl_chart(self, daily_pnl_dollars: List[Tuple[date, float]]) -> str:
        """Delegate to the helper that renders the cumulative P&L chart."""
        return await _generate_cumulative_pnl_chart_impl(self, daily_pnl_dollars)

    def _generate_station_breakdown_chart(self, station_breakdown: Dict[str, int]) -> str:
        """Delegate to the helper that renders the station breakdown chart."""
        return _generate_station_breakdown_chart_impl(self, station_breakdown)

    def _generate_rule_breakdown_chart(self, rule_breakdown: Dict[str, int]) -> str:
        """Delegate to the helper that renders the rule breakdown chart."""
        return _generate_rule_breakdown_chart_impl(self, rule_breakdown)


async def _generate_daily_pnl_chart_impl(self: "PnlChartRendererMixin", daily_pnl_data: List[Tuple[date, float]]) -> str:
    if not daily_pnl_data:
        raise InsufficientDataError("No daily P&L data available")
    timestamps = [datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc) for day, _ in daily_pnl_data]
    values = [float(value) for _, value in daily_pnl_data]
    return await self.generate_unified_chart(
        timestamps=timestamps,
        values=values,
        chart_title="Daily P&L (Percentage)",
        y_label="",
        value_formatter_func=lambda value: f"{value:+.2f}%",
        is_pnl_chart=True,
    )


async def _generate_cumulative_pnl_chart_impl(self: "PnlChartRendererMixin", daily_pnl_dollars: List[Tuple[date, float]]) -> str:
    if not daily_pnl_dollars:
        raise InsufficientDataError("No cumulative P&L data available")
    timestamps = [datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc) for day, _ in daily_pnl_dollars]
    cumulative_cents = np.cumsum([float(value) for _, value in daily_pnl_dollars])
    values = list(cumulative_cents / 100.0)
    return await self.generate_unified_chart(
        timestamps=timestamps,
        values=values,
        chart_title="Cumulative P&L (Dollars)",
        y_label="",
        value_formatter_func=lambda value: f"${value:+.2f}",
        is_pnl_chart=True,
    )


def _generate_station_breakdown_chart_impl(self: "PnlChartRendererMixin", station_breakdown: Dict[str, int]) -> str:
    renderer = PnlBreakdownChartRenderer(
        chart_width_inches=self.chart_width_inches,
        chart_height_inches=self.chart_height_inches,
        dpi=self.dpi,
    )
    return renderer.generate_breakdown_chart(
        data=station_breakdown,
        title="Station P&L Breakdown",
        xlabel="Station",
        filename_suffix="station.png",
        np=np,
        plt=plt,
        tempfile=tempfile,
    )


def _generate_rule_breakdown_chart_impl(self: "PnlChartRendererMixin", rule_breakdown: Dict[str, int]) -> str:
    renderer = PnlBreakdownChartRenderer(
        chart_width_inches=self.chart_width_inches,
        chart_height_inches=self.chart_height_inches,
        dpi=self.dpi,
    )
    return renderer.generate_breakdown_chart(
        data=rule_breakdown,
        title="Rule P&L Breakdown",
        xlabel="Rule",
        filename_suffix="rule.png",
        np=np,
        plt=plt,
        tempfile=tempfile,
    )


async def _render_chart(self: PnlChartRendererMixin, generator, dataset) -> str:
    result = generator(dataset)
    if inspect.isawaitable(result):
        return await result
    return result


def _cleanup_partial_charts(chart_paths: Sequence[str]) -> None:
    for path in chart_paths:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except OSError:
            logger.warning("Unable to clean up P&L chart %s", path)
