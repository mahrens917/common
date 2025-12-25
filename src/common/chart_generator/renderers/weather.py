from __future__ import annotations

import logging
import sys
from typing import Any, List, Optional, Tuple

from common.chart_generator_helpers.astronomical_calculator import AstronomicalCalculator
from common.chart_generator_helpers.weather_charts_orchestrator import (
    WeatherChartsOrchestrator,
)
from common.chart_generator_helpers.weather_station_loader import WeatherStationLoader

from ..contexts import WeatherChartSeries
from ..dependencies import os as dependencies_os
from .base import UnifiedChartRendererMixin

logger = logging.getLogger("src.monitor.chart_generator")

# Expected coordinate tuple length
_COORDINATE_TUPLE_LENGTH = 2


class WeatherChartRendererMixin(UnifiedChartRendererMixin):
    async def generate_weather_charts(self) -> List[str]:
        """Render temperature charts for every configured station."""
        chart_module = sys.modules.get("src.monitor.chart_generator")
        os_module = getattr(self, "_weather_config_os", None)
        if os_module is None:
            os_module = getattr(chart_module, "os", dependencies_os)
        open_fn = getattr(self, "_weather_config_open", None)
        if open_fn is None:
            open_fn = getattr(chart_module, "open", open)

        orchestrator = WeatherChartsOrchestrator(
            create_weather_chart_func=self._create_weather_chart,
            config_loader_kwargs={"os_module": os_module, "open_fn": open_fn},
        )
        return await orchestrator.generate_weather_charts()

    async def _create_weather_chart(
        self,
        station_icao: str,
        station_name: str,
        city_name: str,
        station_coordinates: Optional[Tuple[float, float]] = None,
    ) -> str:
        sanitized_coordinates = self._sanitize_station_coordinates(station_icao, station_coordinates)

        loader = WeatherStationLoader()
        series = await loader.load_station_temperature_series(station_icao)

        calculator = AstronomicalCalculator()
        astronomical = calculator.compute_astronomical_features(station_icao, sanitized_coordinates, series.timestamps)

        chart_title = self._format_weather_chart_title(station_name, station_icao, series)
        kalshi_strikes = await self._load_kalshi_strikes_with_logging(station_icao)

        return await self._generate_unified_chart(
            timestamps=series.timestamps,
            values=series.temperatures,
            chart_title=chart_title,
            y_label="",
            value_formatter_func=lambda value: f"{value:.1f}°F",
            is_temperature_chart=True,
            vertical_lines=astronomical.vertical_lines,
            dawn_dusk_periods=astronomical.dawn_dusk_periods,
            station_coordinates=sanitized_coordinates,
            line_color="#2E5BBA",
            kalshi_strikes=kalshi_strikes,
            station_icao=station_icao,
        )

    def _sanitize_station_coordinates(
        self, station_icao: str, station_coordinates: Optional[Tuple[float, float]]
    ) -> Optional[Tuple[float, float]]:
        if station_coordinates and len(station_coordinates) == _COORDINATE_TUPLE_LENGTH:
            try:
                sanitized = (float(station_coordinates[0]), float(station_coordinates[1]))
            except (TypeError, ValueError):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
                logger.warning("Invalid coordinates provided for %s, dawn/dusk shading disabled", station_icao)
                return None
            logger.info("Using coordinates for %s: %s", station_icao, sanitized)
            return sanitized

        logger.warning("No valid coordinates provided for %s, dawn/dusk shading disabled", station_icao)
        return None

    def _format_weather_chart_title(self, station_name: str, station_icao: str, series: WeatherChartSeries) -> str:
        return f"{station_name} ({station_icao}) - {series.current_temperature:.1f}°F"

    async def _load_kalshi_strikes_with_logging(self, station_icao: str) -> List[Any]:
        try:
            strikes = await self._get_kalshi_strikes_for_station(station_icao)
        except RuntimeError as exc:  # pragma: no cover - redis failure
            logger.warning("Failed to fetch Kalshi strikes for %s: %s", station_icao, exc)
            if str(exc).startswith("No Kalshi strikes available"):
                return []
            raise
        except (ValueError, OSError) as exc:  # pragma: no cover - redis failure
            logger.warning("Failed to fetch Kalshi strikes for %s: %s", station_icao, exc)
            raise

        if strikes:
            logger.info("Found %s Kalshi strikes for %s: %s", len(strikes), station_icao, strikes)
        else:
            logger.debug("No Kalshi strikes found for %s", station_icao)
        return strikes

    async def _get_kalshi_strikes_for_station(self, station_icao: str) -> List[float]:
        """Stub for the actual implementation provided by ChartGenerator."""
        raise NotImplementedError
