from __future__ import annotations

"""Helper for initializing ChartGenerator components"""


import logging
import sys
from typing import Optional

from common.config.redis_schema import get_schema_config
from common.history_tracker import WeatherHistoryTracker
from src.common.price_path_calculator import MostProbablePricePathCalculator

from .chart_file_manager import ChartFileManager
from .chart_styler import ChartStyler
from .city_token_resolver import CityTokenResolver
from .kalshi_strike_collector import KalshiStrikeCollector
from .load_chart_creator import LoadChartCreator
from .price_chart_creator import PriceChartCreator
from .progress_notifier import ProgressNotifier
from .system_chart_creator import SystemChartCreator
from .time_axis_configurator import TimeAxisConfigurator

logger = logging.getLogger("src.monitor.chart_generator")


class ChartGeneratorInitializer:
    """Initializes all ChartGenerator components and styling"""

    @staticmethod
    def initialize_components(
        *,
        price_path_calculator: Optional[MostProbablePricePathCalculator],
        prediction_horizon_days: int,
        progress_callback,
        generate_unified_chart_func,
    ) -> dict:
        """Initialize all chart generator components and return as dict"""
        styler = ChartStyler()
        schema = get_schema_config()

        cg_module = sys.modules.get("src.monitor.chart_generator")
        tracker_cls = getattr(cg_module, "WeatherHistoryTracker", WeatherHistoryTracker)
        weather_history_tracker = tracker_cls()

        if price_path_calculator is not None:
            calculator = price_path_calculator
        else:
            calculator_cls = getattr(
                cg_module,
                "MostProbablePricePathCalculator",
                MostProbablePricePathCalculator,
            )
            from src.common.price_path_calculator_helpers.config import PricePathCalculatorConfig

            config = PricePathCalculatorConfig(
                strike_count=64,
                min_moneyness=0.8,
                max_moneyness=1.2,
                timeline_points=10,
                min_horizon_days=0.5,
                surface_loader=None,
                progress_callback=progress_callback,
                dependencies=None,
            )
            calculator = calculator_cls(config=config)

        progress_notifier = ProgressNotifier(progress_callback)

        load_chart_creator = LoadChartCreator(
            primary_color=styler.primary_color,
            generate_unified_chart_func=generate_unified_chart_func,
        )
        system_chart_creator = SystemChartCreator(
            primary_color=styler.primary_color,
            generate_unified_chart_func=generate_unified_chart_func,
        )
        price_chart_creator = PriceChartCreator(
            primary_color=styler.primary_color,
            price_path_calculator=calculator,
            price_path_horizon_days=prediction_horizon_days,
            progress_notifier=progress_notifier,
            generate_unified_chart_func=generate_unified_chart_func,
        )

        return {
            "styler": styler,
            "schema": schema,
            "weather_history_tracker": weather_history_tracker,
            "price_path_calculator": calculator,
            "price_path_horizon_days": prediction_horizon_days,
            "file_manager": ChartFileManager(),
            "progress_notifier": progress_notifier,
            "time_configurator": TimeAxisConfigurator(),
            "token_resolver": CityTokenResolver(),
            "strike_collector": KalshiStrikeCollector(),
            "load_chart_creator": load_chart_creator,
            "system_chart_creator": system_chart_creator,
            "price_chart_creator": price_chart_creator,
        }
