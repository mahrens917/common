from __future__ import annotations

"""Helper for orchestrating weather chart generation across multiple stations"""


import asyncio
import logging
from typing import Any, Dict, List

logger = logging.getLogger("src.monitor.chart_generator")


class WeatherChartsOrchestrator:
    """Orchestrates weather chart generation for multiple stations"""

    def __init__(
        self,
        *,
        create_weather_chart_func,
        config_loader_kwargs: Dict[str, Any] | None = None,
    ):
        self.create_weather_chart_func = create_weather_chart_func
        self._config_loader_kwargs = config_loader_kwargs or {}

    async def generate_weather_charts(self) -> List[str]:
        """Render temperature charts for every configured station."""
        from .orchestrator_helpers.chart_generator import generate_charts_for_stations
        from .orchestrator_helpers.cleanup_handler import cleanup_chart_files
        from .orchestrator_helpers.config_loader import load_weather_station_config

        weather_stations = load_weather_station_config(**self._config_loader_kwargs)
        chart_paths: List[str] = []

        try:
            await generate_charts_for_stations(
                weather_stations,
                self.create_weather_chart_func,
                chart_paths=chart_paths,
            )
        except asyncio.CancelledError:
            cleanup_chart_files(chart_paths)
            raise
        except (IOError, OSError, ValueError, RuntimeError):
            cleanup_chart_files(chart_paths)
            raise
        else:
            return chart_paths
