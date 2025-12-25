from __future__ import annotations

"""Shared helpers for loading weather-related configuration files."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


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
            return module.load_config_json
        except (ImportError, ModuleNotFoundError, AttributeError):
            continue

    raise WeatherConfigError("weather package is not installed")


def load_weather_station_mapping(
    *,
    config_dir: Optional[Path] = None,
) -> Dict[str, Dict[str, Any]]:
    """Return the weather station mapping keyed by city code."""
    data = _resolve_config_json(
        "weather_station_mapping.json",
        config_dir if config_dir is not None else None,
    )
    mappings = data.get("mappings")
    if not isinstance(mappings, dict):
        raise WeatherConfigError("weather_station_mapping.json missing 'mappings' object")
    return mappings


def load_weather_trading_config(
    *,
    config_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Return the weather trading configuration."""
    return _resolve_config_json(
        "weather_trading_config.json",
        config_dir if config_dir is not None else None,
    )


__all__ = [
    "WeatherConfigError",
    "load_weather_station_mapping",
    "load_weather_trading_config",
]
