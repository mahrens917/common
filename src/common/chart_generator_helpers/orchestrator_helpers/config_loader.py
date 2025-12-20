"""Load weather station configuration."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from common.config_loader import BaseConfigLoader
from src.common.chart_generator.exceptions import InsufficientDataError

logger = logging.getLogger("src.monitor.chart_generator")
_CONFIG_DIR = Path("config")
_FILENAME = "weather_station_mapping.json"
_base_loader = BaseConfigLoader(_CONFIG_DIR)


def load_weather_station_config(
    os_module=os,
    open_fn=open,
    config_loader: BaseConfigLoader | None = None,
) -> dict:
    """
    Load weather station configuration from JSON file.

    Returns:
        Dictionary of weather station mappings

    Raises:
        InsufficientDataError: If configuration cannot be loaded or is empty
    """
    try:
        weather_config = _load_weather_config(
            os_module=os_module,
            open_fn=open_fn,
            config_loader=config_loader,
        )
    except (FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        raise InsufficientDataError("Failed to load weather station configuration") from exc

    # Mappings section is required in weather_station_mapping.json
    weather_stations = weather_config.get("mappings")
    if not weather_stations:
        raise InsufficientDataError("No weather stations configured")

    return weather_stations


def _load_weather_config(
    os_module=os,
    open_fn=open,
    config_loader: BaseConfigLoader | None = None,
) -> Dict[str, Any]:
    """Load the raw weather station mapping payload."""
    preferred_loader = config_loader or _base_loader
    if config_loader is None and os_module is os and open_fn is open:
        return preferred_loader.load_json_file(_FILENAME)

    config_path = Path(os_module.path.join(str(_CONFIG_DIR), _FILENAME))
    with open_fn(config_path, "r", encoding="utf-8") as handle:
        return json.load(handle)
