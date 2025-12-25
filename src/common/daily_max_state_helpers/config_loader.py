"""Configuration loading for DailyMaxState."""

import logging
from pathlib import Path
from typing import Any, Dict

from common.config_loader import BaseConfigLoader
from common.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class MetarConfigLoadError(RuntimeError):
    """Raised when the METAR configuration cannot be loaded."""


class ConfigLoader:
    """Loads METAR configuration for safety margins."""

    def __init__(self) -> None:
        config_dir = Path(__file__).resolve().parents[3] / "config"
        self._loader = BaseConfigLoader(config_dir)

    def load_metar_config(self) -> Dict[str, Any]:
        """Load METAR data source configuration for safety margins.

        Returns:
            Mapping containing source configuration.

        Raises:
            MetarConfigLoadError: If the configuration file cannot be read or is invalid.
        """
        try:
            config_data = self._loader.load_json_file("metar_data_sources.json")
        except FileNotFoundError as exc:
            raise MetarConfigLoadError("METAR config file not found") from exc
        except ConfigurationError as exc:
            raise MetarConfigLoadError(str(exc)) from exc
        except OSError as exc:
            raise MetarConfigLoadError("Failed to read METAR config") from exc

        try:
            data_sources = self._loader.get_section(config_data, "data_sources")
        except ConfigurationError as exc:
            raise MetarConfigLoadError(str(exc)) from exc

        if not data_sources:
            raise MetarConfigLoadError("METAR config contains no data source definitions")

        logger.debug("Loaded METAR config from %s", self._loader.config_dir / "metar_data_sources.json")
        return data_sources
