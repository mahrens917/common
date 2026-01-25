from __future__ import annotations

"""Shared helpers for loading weather-related configuration files."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from common.config_loader import load_config

logger = logging.getLogger(__name__)

# Base directory for all projects (configurable via env for flexibility)
_PROJECTS_BASE = Path(os.environ.get("PROJECTS_BASE", Path.home() / "projects"))


class WeatherConfigError(RuntimeError):
    """Raised when required weather configuration assets cannot be loaded."""


def _load_from_directory(name: str, directory: Path) -> Dict[str, Any]:
    config_path = directory / name
    if not config_path.exists():
        raise WeatherConfigError(f"Weather config not found: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise WeatherConfigError(f"Invalid JSON in {config_path}") from exc
    except OSError as exc:
        raise WeatherConfigError(f"Unable to read {config_path}") from exc


def _resolve_config_json(name: str, config_dir: Optional[Path]) -> Dict[str, Any]:
    if config_dir is not None:
        return _load_from_directory(name, config_dir)

    local_config_dir = Path.cwd() / "config"
    if local_config_dir.exists():
        config_path = local_config_dir / name
        if config_path.exists():
            return _load_from_directory(name, local_config_dir)

    load_config_json = _import_config_loader()
    try:
        return load_config_json(name)
    except (WeatherConfigError, OSError) as exc:
        raise WeatherConfigError(str(exc)) from exc


def _import_config_loader():
    """Import config loader from weather package with fallback."""
    import importlib

    for module_path in ["src.weather.config_loader", "weather.config_loader"]:
        try:
            module = importlib.import_module(module_path)
        except (
            ImportError,
            ModuleNotFoundError,
            AttributeError,
        ):  # Expected exception - optional dependency  # policy_guard: allow-silent-handler
            continue
        else:
            return module.load_config_json

    raise WeatherConfigError("weather package is not installed")


def load_weather_station_mapping(
    *,
    config_dir: Optional[Path] = None,
) -> Dict[str, Dict[str, Any]]:
    """Return the weather station mapping keyed by city code."""
    if config_dir is not None:
        data = _load_from_directory("stations.json", config_dir)
    else:
        data = load_config("stations.json", package="common")
    stations = data.get("stations")
    if not isinstance(stations, dict):
        raise WeatherConfigError("stations.json missing 'stations' object")
    mappings: Dict[str, Dict[str, Any]] = {}
    for icao, station_info in stations.items():
        city_code = station_info.get("city_code")
        if city_code:
            mappings[city_code] = station_info
    return mappings


def load_weather_trading_config(
    *,
    config_dir: Optional[Path] = None,
    package: Optional[str] = None,
) -> Dict[str, Any]:
    """Return the weather trading configuration.

    Args:
        config_dir: Optional explicit config directory path.
        package: Optional package name to load config from (e.g., 'weather').
                 When specified, loads from ~/projects/{package}/config/.
                 Takes precedence over config_dir when both are specified.

    Returns:
        Dictionary containing the weather trading configuration.
    """
    if config_dir is not None:
        return _load_from_directory("weather_trading_config.json", config_dir)
    if package is not None:
        resolved_dir = _PROJECTS_BASE / package / "config"
        if not resolved_dir.exists():
            raise WeatherConfigError(f"Config directory not found for package '{package}': {resolved_dir}")
        return _load_from_directory("weather_trading_config.json", resolved_dir)
    return load_config("weather_trading_config.json", package="weather")


def _get_weather_settings_func():
    """Load weather settings loader with fallback for when package not installed."""
    import importlib

    for module_path in ["src.weather.settings", "weather.settings"]:
        try:
            module = importlib.import_module(module_path)
        except (
            ImportError,
            ModuleNotFoundError,
            AttributeError,
        ):  # Expected exception - optional dependency  # policy_guard: allow-silent-handler
            continue
        else:
            return module.get_weather_settings

    def get_weather_settings():
        """Fallback when weather package is not installed."""
        from types import SimpleNamespace

        return SimpleNamespace(sources=SimpleNamespace(asos_source=None, metar_source=None))

    return get_weather_settings


get_weather_settings = _get_weather_settings_func()


__all__ = [
    "WeatherConfigError",
    "get_weather_settings",
    "load_weather_station_mapping",
    "load_weather_trading_config",
]
