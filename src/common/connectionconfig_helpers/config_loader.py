"""Configuration loading helpers for ConnectionConfig.

Delegates to BaseConfigLoader for JSON loading operations.
"""

import logging
from typing import Any, Dict, Optional

from common.config import env_float, env_int
from common.config.errors import ConfigurationError
from common.config_loader import load_config
from common.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

_DEFAULT_INT_VALUES = {
    "CONNECTION_TIMEOUT_SECONDS": 30,
    "REQUEST_TIMEOUT_SECONDS": 15,
    "MAX_IDLE_SECONDS": 600,
    "RECONNECTION_INITIAL_DELAY_SECONDS": 2,
    "RECONNECTION_MAX_DELAY_SECONDS": 300,
    "MAX_CONSECUTIVE_FAILURES": 10,
    "HEALTH_CHECK_INTERVAL_SECONDS": 60,
    "TELEGRAM_NOTIFICATION_THROTTLE_SECONDS": 300,
    "SUBSCRIPTION_TIMEOUT_SECONDS": 120,
    "MAX_SUBSCRIPTION_RETRY_ATTEMPTS": 3,
    "SUBSCRIPTION_BACKOFF_MULTIPLIER_SECONDS": 5,
}

_DEFAULT_FLOAT_VALUES = {
    "RECONNECTION_BACKOFF_MULTIPLIER": 2.0,
    "SUBSCRIPTION_INITIAL_DELAY_SECONDS": 0.5,
    "SUBSCRIPTION_PROCESSING_DELAY_SECONDS": 0.5,
}


def require_env_int(name: str) -> int:
    """Get an environment variable as integer, using default if available."""
    value = env_int(name, or_value=None, required=False)
    if value is not None:
        return value
    if name in _DEFAULT_INT_VALUES:
        return _DEFAULT_INT_VALUES[name]
    raise ConfigurationError(f"Environment variable {name} must be defined")


def require_env_float(name: str) -> float:
    """Get an environment variable as float, using default if available."""
    value = env_float(name, or_value=None, required=False)
    if value is not None:
        return value
    if name in _DEFAULT_FLOAT_VALUES:
        return _DEFAULT_FLOAT_VALUES[name]
    raise ConfigurationError(f"Environment variable {name} must be defined")


def resolve_cfb_setting(
    value: Optional[int],
    *,
    configured_value: Optional[int] = None,
    default_value: Optional[int] = None,
) -> int:
    """Resolve CFB-specific setting using configured/default value when not specified."""
    reference_value = configured_value if configured_value is not None else default_value
    if reference_value is None:
        raise ConfigurationError("Either configured_value or default_value is required")
    return reference_value if value is None else value


def load_websocket_config() -> Dict[str, Any]:
    """
    Load WebSocket configuration from JSON file.

    Delegates to canonical load_config() for consistent JSON loading.

    Returns:
        Dictionary containing WebSocket configuration, or empty dict if file not found

    Raises:
        ConfigurationError: If file exists but contains invalid JSON
    """
    try:
        return load_config("websocket_config.json")
    except FileNotFoundError:  # Expected exception in operation  # policy_guard: allow-silent-handler
        logger.debug("Expected exception in operation")
        return {}


def load_weather_config() -> Dict[str, Any]:
    """
    Load weather service configuration from JSON file.

    Delegates to canonical load_config() for consistent JSON loading,
    then extracts only the timeout values needed.

    Returns:
        Dictionary containing weather service timeout configuration

    Raises:
        FileNotFoundError: If weather_config.json not found
        ConfigurationError: If config is invalid or missing required fields
    """
    try:
        config = load_config("weather_config.json", package="weather")
    except FileNotFoundError as exc:
        raise FileNotFoundError("Weather config file not found") from exc

    try:
        # Extract all connection config values
        return {
            "connection_timeout_seconds": config["connection_timeout_seconds"],
            "request_timeout_seconds": config["request_timeout_seconds"],
            "reconnection_initial_delay_seconds": config["reconnection_initial_delay_seconds"],
            "reconnection_max_delay_seconds": config["reconnection_max_delay_seconds"],
            "reconnection_backoff_multiplier": config["reconnection_backoff_multiplier"],
            "max_consecutive_failures": config["max_consecutive_failures"],
            "health_check_interval_seconds": config["health_check_interval_seconds"],
            "subscription_timeout_seconds": config["subscription_timeout_seconds"],
        }
    except KeyError as exc:
        raise ConfigurationError("Invalid weather config file: missing required field") from exc
