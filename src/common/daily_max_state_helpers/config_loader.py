"""METAR configuration loader for daily max state processing."""

from __future__ import annotations

from pathlib import Path

from common.config_loader import BaseConfigLoader

_WEATHER_CONFIG_DIR = Path.home() / "projects" / "weather" / "config"


class MetarConfigLoadError(Exception):
    """Raised when METAR configuration cannot be loaded or is invalid."""


class ConfigLoader:
    """Loads METAR data source configuration from the weather config directory."""

    def __init__(self) -> None:
        self._loader = BaseConfigLoader(_WEATHER_CONFIG_DIR)

    def load_metar_config(self) -> dict:
        """Load and return the data_sources section of the METAR configuration.

        Raises:
            MetarConfigLoadError: If the config file is missing or data_sources is empty.
        """
        try:
            data = self._loader.load_json_file("metar_config.json")
        except FileNotFoundError as exc:
            raise MetarConfigLoadError("METAR configuration file not found") from exc

        data_sources = data["data_sources"]
        if not data_sources:
            raise MetarConfigLoadError("METAR configuration contains no data sources")
        return data_sources


__all__ = ["ConfigLoader", "MetarConfigLoadError"]
