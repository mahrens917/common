"""Generate charts for weather stations."""

import asyncio
import logging
from typing import Callable, List, Optional

from common.chart_generator.exceptions import InsufficientDataError

logger = logging.getLogger("src.monitor.chart_generator")


async def generate_charts_for_stations(
    weather_stations: dict,
    create_weather_chart_func: Callable,
    *,
    chart_paths: Optional[List[str]] = None,
) -> List[str]:
    """
    Generate charts for all weather stations.

    Returns:
        List of chart paths.

    Raises:
        InsufficientDataError: If no charts were generated.
    """
    if chart_paths is None:
        chart_paths = []

    for city_code, station_info in weather_stations.items():
        station_icao = station_info.get("icao")
        if not station_icao:
            logger.warning("Skipping station without ICAO: %s", station_info)
            continue

        station_name = station_info.get("name", station_icao)
        city_name = station_info.get("city", city_code)
        station_coordinates = (
            station_info.get("latitude"),
            station_info.get("longitude"),
        )

        try:
            chart_path = await create_weather_chart_func(
                station_icao,
                station_name,
                city_name,
                station_coordinates,
            )
        except InsufficientDataError as exc:
            logger.warning("Skipping %s: %s", station_icao, exc)
            continue
        except asyncio.CancelledError:
            raise
        except (
            IOError,
            OSError,
            ValueError,
            RuntimeError,
        ):  # pragma: no cover - unexpected renderer failure
            logger.exception("Failed to generate chart for %s", station_icao)
            continue

        chart_paths.append(chart_path)
        logger.info("Generated weather chart for %s", station_icao)

    if not chart_paths:
        raise InsufficientDataError("No weather data available for any station")

    return chart_paths
