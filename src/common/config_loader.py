"""
Configuration loader utilities for centralized config management.

This module provides:
1. BaseConfigLoader - Reusable base class for all config loaders
2. load_config() - Simple function for loading config files
3. Domain-specific loaders (load_pnl_config, load_weather_trading_config)

All config loaders in the codebase should either:
- Use load_config() for simple JSON loading
- Inherit from BaseConfigLoader for more sophisticated needs
- Delegate to BaseConfigLoader methods
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

from common.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


def _resolve_config_dir() -> Path:
    repo_config_dir = Path.cwd() / "config"
    if repo_config_dir.exists():
        return repo_config_dir
    return Path(__file__).parent.parent.parent / "config"


_CONFIG_DIR = _resolve_config_dir()


class BaseConfigLoader:
    """
    Base configuration loader providing standard JSON loading patterns.

    All config loaders should either inherit from this class or delegate to it
    to ensure consistent error handling and loading behavior.

    Example usage:
        # Inherit:
        class MyConfigLoader(BaseConfigLoader):
            def __init__(self):
                super().__init__(Path("path/to/config"))

        # Or delegate:
        loader = BaseConfigLoader(Path("path/to/config"))
        config = loader.load_json_file("myconfig.json")
    """

    def __init__(self, config_dir: Path):
        """
        Initialize config loader with a configuration directory.

        Args:
            config_dir: Path to the configuration directory
        """
        self.config_dir = config_dir
        self._cached_config: Optional[Dict[str, Any]] = None

    def load_json_file(self, filename: str) -> Dict[str, Any]:
        """
        Load a JSON configuration file from the config directory.

        Args:
            filename: Name of the config file (e.g., 'validation_constants.json')

        Returns:
            Dictionary containing the configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            ConfigurationError: If config file is invalid JSON
        """
        config_path = self.config_dir / filename

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except json.JSONDecodeError as exc:  # policy_guard: allow-silent-handler
            raise ConfigurationError(f"Invalid JSON in config file {filename}") from exc

    def get_section(self, config: Dict[str, Any], section_name: str) -> Dict[str, Any]:
        """
        Get a specific section from configuration dictionary.

        Args:
            config: Configuration dictionary
            section_name: Name of section to retrieve

        Returns:
            Section dictionary

        Raises:
            ConfigurationError: If section not found
        """
        if section_name not in config:
            raise ConfigurationError(f"Configuration section not found: {section_name}")

        section = config[section_name]
        if not isinstance(section, dict):
            raise ConfigurationError(f"Configuration section '{section_name}' must be a dict, got {type(section)}")

        return section

    def get_parameter(self, config: Dict[str, Any], section_name: str, parameter_name: str) -> Any:
        """
        Get a specific parameter from a configuration section.

        Args:
            config: Configuration dictionary
            section_name: Name of section containing the parameter
            parameter_name: Name of parameter to retrieve

        Returns:
            Parameter value

        Raises:
            ConfigurationError: If section or parameter not found
        """
        section = self.get_section(config, section_name)
        if parameter_name not in section:
            raise ConfigurationError(f"Parameter '{parameter_name}' not found in section '{section_name}'")
        return section[parameter_name]


def load_config(filename: str) -> Dict[str, Any]:
    """
    Load a configuration file from the config directory.

    This is a convenience function that delegates to BaseConfigLoader.
    Use this for simple config loading. For more sophisticated needs,
    use BaseConfigLoader directly or inherit from it.

    Args:
        filename: Name of the config file (e.g., 'validation_constants.json')

    Returns:
        Dictionary containing the configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        ConfigurationError: If config file is invalid JSON
    """
    loader = BaseConfigLoader(_CONFIG_DIR)
    return loader.load_json_file(filename)


def load_pnl_config() -> Dict[str, Any]:
    """
    Load PnL configuration from config/pnl_config.json.

    Returns:
        Dictionary containing PnL configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
        RuntimeError: If config is missing required fields
    """
    config_path = _CONFIG_DIR / "pnl_config.json"

    if not config_path.exists():
        raise FileNotFoundError(f"PnL config file not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            config = json.load(handle)

        # Validate required sections exist
        if "trade_collection" not in config:
            raise RuntimeError("Missing 'trade_collection' section in PnL config")

        if "historical_start_date" not in config["trade_collection"]:
            raise RuntimeError("Missing 'historical_start_date' in trade_collection config")

    except json.JSONDecodeError as exc:  # policy_guard: allow-silent-handler
        raise RuntimeError("Invalid JSON in PnL config file") from exc
    else:
        return config


def get_historical_start_date() -> date:
    """
    Get the historical start date from PnL configuration.

    This is the single source of truth for the minimum trade date.
    All trades before this date should be filtered out.

    Returns:
        Date object representing the historical start date (inclusive)

    Raises:
        RuntimeError: If config is invalid or date cannot be parsed
    """
    try:
        config = load_pnl_config()
        date_str = config["trade_collection"]["historical_start_date"]

        # Parse the date string (expected format: YYYY-MM-DD)
        start_date = date.fromisoformat(date_str)

        logger.debug(f"Loaded historical start date: {start_date}")

    except ValueError as exc:  # policy_guard: allow-silent-handler
        raise RuntimeError("Invalid date format in historical_start_date") from exc
    except (FileNotFoundError, RuntimeError, KeyError, TypeError, OSError) as exc:  # policy_guard: allow-silent-handler
        raise RuntimeError(f"Failed to load historical start date: {exc}") from exc
    else:
        return start_date


def get_reporting_timezone() -> str:
    """
    Retrieve the configured reporting timezone from the shared PnL configuration.

    Args:
        None

    Returns:
        Configured timezone value.

    Raises:
        RuntimeError: If the timezone configuration is unavailable or invalid.
    """
    try:
        config = load_pnl_config()
    except (FileNotFoundError, RuntimeError, OSError) as exc:  # policy_guard: allow-silent-handler
        raise RuntimeError("Failed to load PnL config for timezone lookup") from exc

    reporting: Optional[Dict[str, Any]] = config.get("reporting")
    if not isinstance(reporting, dict):
        raise TypeError("PnL config missing 'reporting' section")

    timezone_value = reporting.get("timezone")
    if not isinstance(timezone_value, str):
        raise TypeError("PnL config must define a non-empty reporting timezone value")
    timezone_value = timezone_value.strip()
    if not timezone_value:
        raise RuntimeError("PnL config must define a non-empty reporting timezone value")

    return timezone_value


def load_weather_trading_config() -> Dict[str, Any]:
    """
    Load the weather trading configuration from config/weather_trading_config.json.

    Returns:
        Dictionary containing weather trading configuration values.

    Raises:
        FileNotFoundError: If the configuration file is missing.
        RuntimeError: If the file content cannot be decoded as valid JSON.
    """
    config_path = _CONFIG_DIR / "weather_trading_config.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Weather trading config file not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:  # policy_guard: allow-silent-handler
        raise RuntimeError("Invalid JSON in weather trading config file") from exc


__all__ = [
    "BaseConfigLoader",
    "load_config",
    "load_pnl_config",
    "load_weather_trading_config",
    "get_historical_start_date",
    "get_reporting_timezone",
]
