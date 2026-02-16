"""Professional chart generator for history monitoring and price visualization."""

from __future__ import annotations

import logging
import sys
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, cast

logger = logging.getLogger(__name__)

from common.chart_generator_helpers.chart_file_manager import ChartFileManager
from common.chart_generator_helpers.chart_generator_initializer import (
    ChartGeneratorInitializer,
)
from common.chart_generator_helpers.load_charts_generator import LoadChartsGenerator
from common.chart_generator_helpers.progress_notifier import ProgressNotifier
from common.price_path_calculator import MostProbablePricePathCalculator

from .dependencies import os as dependencies_os
from .dependencies import plt
from .renderers.pnl import PnlChartRendererMixin
from .renderers.weather import WeatherChartRendererMixin
from .runtime_helpers import cleanup_chart_files as _cleanup_chart_files_impl
from .runtime_helpers import cleanup_single_chart_file as _cleanup_single_chart_file_impl
from .runtime_helpers import configure_price_chart_axis as _configure_price_chart_axis_impl
from .runtime_helpers import configure_time_axis as _configure_time_axis_impl
from .runtime_helpers import configure_time_axis_with_5_minute_alignment as _configure_time_axis_with_5_minute_alignment_impl
from .runtime_helpers import create_load_chart as _create_load_chart_impl
from .runtime_helpers import create_price_chart_impl as _create_price_chart_impl
from .runtime_helpers import create_system_chart as _create_system_chart_impl
from .runtime_helpers import generate_load_charts as _generate_load_charts_impl
from .runtime_helpers import generate_price_chart_with_path as _generate_price_chart_with_path_impl
from .runtime_helpers import get_city_tokens_for_icao as _get_city_tokens_for_icao_impl
from .runtime_helpers import get_kalshi_strikes_for_station as _get_kalshi_strikes_for_station_impl
from .runtime_helpers import notify_progress as _notify_progress_impl
from .runtime_helpers import safe_float_value as _safe_float_value_impl


def _check_market_expires_today(strike_collector, market_data, today_date, et_timezone, market_key, today_market_date) -> bool:
    """Check whether a market expires today via the strike collector's validator."""
    validator = getattr(strike_collector, "expiration_validator", None)
    if validator is None:
        raise RuntimeError("Strike collector has no expiration validator configured")
    base_method = getattr(type(validator), "market_expires_today", None)
    if base_method is None:
        raise RuntimeError("Expiration validator is missing market_expires_today")
    try:
        return base_method(validator, market_data, today_date, et_timezone, market_key, today_market_date)
    except RuntimeError as exc:
        message = str(exc)
        if "No expiration metadata available" in message:
            raise RuntimeError("Unable to determine expiration date") from exc
        raise


class ChartPropertyMixin:
    _progress_callback: Optional[Callable[[str], None]]
    _progress_notifier: Optional[ProgressNotifier]
    _price_chart_creator: Any
    _time_configurator: Any
    _file_manager: ChartFileManager
    _load_charts_generator: LoadChartsGenerator | None
    _strike_collector: Any

    @property
    def progress_callback(self):
        return self._progress_callback

    @property
    def progress_notifier(self):
        return self._progress_notifier

    @progress_notifier.setter
    def progress_notifier(self, value):
        self._progress_notifier = value

    @property
    def price_chart_creator(self):
        return self._price_chart_creator

    @price_chart_creator.setter
    def price_chart_creator(self, value):
        self._price_chart_creator = value

    @property
    def time_configurator(self):
        return self._time_configurator

    @property
    def chart_file_manager(self):
        if hasattr(self, "_chart_file_manager"):
            return self._chart_file_manager
        return getattr(self, "_file_manager", None)

    @chart_file_manager.setter
    def chart_file_manager(self, value):
        self._chart_file_manager = value
        self._file_manager = value

    @property
    def load_charts_generator(self) -> LoadChartsGenerator | None:
        return self._load_charts_generator

    @property
    def strike_collector(self):
        return self._strike_collector


class ChartCreationMixin:
    _create_load_chart: Callable[[str, int], Awaitable[str]]
    _create_system_chart: Callable[[str, int], Awaitable[str]]
    _create_price_chart: Callable[[str, Optional[int]], Awaitable[str]]
    _get_city_tokens_for_icao: Callable[[str], Awaitable[Tuple[List[str], Optional[str]]]]

    async def create_load_chart(self, service_name: str, hours: int) -> str:
        return await self._create_load_chart(service_name, hours)

    async def create_system_chart(self, metric: str, hours: int) -> str:
        return await self._create_system_chart(metric, hours)

    async def create_price_chart(self, symbol: str, prediction_horizon_days: Optional[int] = None) -> str:
        return await self._create_price_chart(symbol, prediction_horizon_days)

    async def get_city_tokens_for_icao(self, station_icao: str):
        return await self._get_city_tokens_for_icao(station_icao)


class ChartHelperMixin:
    _strike_collector: Any
    _file_manager: ChartFileManager
    _load_charts_generator: LoadChartsGenerator | None
    _progress_callback: Optional[Callable[[str], None]]
    _progress_notifier: Optional[ProgressNotifier]

    def _market_expires_today(
        self, market_data: Dict[str, str], today_date, et_timezone, market_key: str, today_market_date: str,
    ) -> bool:
        return _check_market_expires_today(self._strike_collector, market_data, today_date, et_timezone, market_key, today_market_date)

    async def generate_load_charts(self, hours: int = 24) -> Dict[str, str]:
        generator = cast("ChartGenerator", self)
        return await _generate_load_charts_impl(generator, hours)

    async def generate_price_chart_with_path(self, symbol: str, prediction_horizon_days: Optional[int] = None) -> str:
        generator = cast("ChartGenerator", self)
        return await _generate_price_chart_with_path_impl(generator, symbol, prediction_horizon_days)

    async def _create_price_chart(self, symbol: str, prediction_horizon_days: Optional[int] = None) -> str:
        generator = cast("ChartGenerator", self)
        return await _create_price_chart_impl(generator, symbol, prediction_horizon_days)

    def _configure_time_axis(
        self,
        ax,
        timestamps,
        chart_type: str = "default",
        station_coordinates=None,
    ):
        generator = cast("ChartGenerator", self)
        return _configure_time_axis_impl(generator, ax, timestamps, chart_type, station_coordinates)

    def _configure_time_axis_with_5_minute_alignment(
        self,
        ax,
        timestamps,
        chart_type: str = "default",
        station_coordinates=None,
    ):
        generator = cast("ChartGenerator", self)
        return _configure_time_axis_with_5_minute_alignment_impl(generator, ax, timestamps, chart_type, station_coordinates)

    def _configure_price_chart_axis(self, ax, timestamps) -> None:
        generator = cast("ChartGenerator", self)
        return _configure_price_chart_axis_impl(generator, ax, timestamps)

    def cleanup_chart_files(self, chart_paths: List[str]):
        generator = cast("ChartGenerator", self)
        return _cleanup_chart_files_impl(generator, chart_paths)

    def cleanup_single_chart_file(self, chart_path: str):
        generator = cast("ChartGenerator", self)
        return _cleanup_single_chart_file_impl(generator, chart_path)

    async def _create_load_chart(self, service_name: str, hours: int) -> str:
        generator = cast("ChartGenerator", self)
        return await _create_load_chart_impl(generator, service_name, hours)

    async def _create_system_chart(self, metric: str, hours: int) -> str:
        generator = cast("ChartGenerator", self)
        return await _create_system_chart_impl(generator, metric, hours)

    async def _get_city_tokens_for_icao(self, station_icao: str):
        generator = cast("ChartGenerator", self)
        return await _get_city_tokens_for_icao_impl(generator, station_icao)

    async def _get_kalshi_strikes_for_station(self, station_icao: str) -> List[float]:
        generator = cast("ChartGenerator", self)
        return await _get_kalshi_strikes_for_station_impl(generator, station_icao)

    def _notify_progress(self, message: str) -> None:
        generator = cast("ChartGenerator", self)
        _notify_progress_impl(generator, message)

    @staticmethod
    def _safe_float(value: str | float | int | None) -> Optional[float]:
        try:
            return _safe_float_value_impl(value)
        except ValueError as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            logger.warning("Failed to convert to float: value=%r, error=%s", value, exc)
            return None


class ChartGenerator(
    ChartPropertyMixin,
    ChartCreationMixin,
    ChartHelperMixin,
    WeatherChartRendererMixin,
    PnlChartRendererMixin,
):
    """Professional chart generator for monitoring KPIs and prices."""

    def __init__(
        self,
        price_path_calculator: Optional[MostProbablePricePathCalculator] = None,
        *,
        prediction_horizon_days: int = 30,
        progress_callback=None,
    ):
        plt.style.use("default")
        self._progress_callback = progress_callback
        components = ChartGeneratorInitializer.initialize_components(
            price_path_calculator=price_path_calculator,
            prediction_horizon_days=prediction_horizon_days,
            progress_callback=progress_callback,
            generate_unified_chart_func=self._generate_unified_chart,
        )
        styler = components["styler"]
        self.chart_width_inches = styler.chart_width_inches
        self.chart_height_inches = styler.chart_height_inches
        self.dpi = styler.dpi
        self.background_color = styler.background_color
        self.grid_color = styler.grid_color
        self.primary_color = styler.primary_color
        self.secondary_color = styler.secondary_color
        self.highlight_color = styler.highlight_color
        self.deribit_color = styler.deribit_color
        self.kalshi_color = styler.kalshi_color
        self.cpu_color = styler.cpu_color
        self.memory_color = styler.memory_color
        self.schema = components["schema"]
        self.weather_history_tracker = components["weather_history_tracker"]
        self.price_path_calculator = components["price_path_calculator"]
        self.price_path_horizon_days = components["price_path_horizon_days"]
        self._chart_file_manager = components["file_manager"]
        self._file_manager = self._chart_file_manager
        self._progress_notifier = components["progress_notifier"]
        self._time_configurator = components["time_configurator"]
        self._token_resolver = components["token_resolver"]
        self._strike_collector = components["strike_collector"]
        self._load_chart_creator = components["load_chart_creator"]
        self._system_chart_creator = components["system_chart_creator"]
        self._price_chart_creator = components["price_chart_creator"]
        self._load_charts_generator = LoadChartsGenerator(
            load_chart_creator=self._load_chart_creator,
            system_chart_creator=self._system_chart_creator,
        )
        chart_module = sys.modules.get("src.monitor.chart_generator")
        self._weather_config_os = getattr(chart_module, "os", dependencies_os)
        self._weather_config_open = getattr(chart_module, "open", open)

    def configure_time_axis_with_5_minute_alignment(
        self,
        ax,
        timestamps,
        chart_type: str = "default",
        station_coordinates=None,
    ):
        return _configure_time_axis_with_5_minute_alignment_impl(self, ax, timestamps, chart_type, station_coordinates)
