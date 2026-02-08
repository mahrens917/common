"""Service-specific configuration builder."""

from typing import Any, Dict

from common.config import env_int
from common.connectionconfig_helpers.config_loader import (
    load_websocket_config,
    resolve_cfb_setting,
)


def build_websocket_config(ws_config: Dict[str, Any]) -> Dict[str, Any]:
    """Build unified websocket configuration from flat config structure.

    Raises:
        KeyError: If required configuration keys are missing from websocket_config.json
    """
    conn = ws_config["connection"]
    sub = ws_config["subscription"]
    return {
        "connection_timeout_seconds": conn["timeout_seconds"],
        "request_timeout_seconds": conn["request_timeout_seconds"],
        "subscription_timeout_seconds": sub["timeout_seconds"],
        "reconnection_initial_delay_seconds": conn["reconnection_initial_delay_seconds"],
        "reconnection_max_delay_seconds": conn["reconnection_max_delay_seconds"],
        "reconnection_backoff_multiplier": conn["reconnection_backoff_multiplier"],
        "max_consecutive_failures": conn["max_consecutive_failures"],
        "health_check_interval_seconds": conn["heartbeat_interval_seconds"],
        "ping_interval_seconds": conn["ping_interval_seconds"],
        "ping_timeout_seconds": conn["ping_timeout_seconds"],
        "close_timeout_seconds": conn["close_timeout_seconds"],
    }


def build_cfb_config() -> Dict[str, Any]:
    """Build CFB scraper service-specific configuration."""
    return {
        "connection_timeout_seconds": resolve_cfb_setting(
            env_int("CFB_CONNECTION_TIMEOUT", or_value=25),
            configured_value=25,
        ),
        "request_timeout_seconds": resolve_cfb_setting(
            env_int("CFB_REQUEST_TIMEOUT", or_value=15),
            configured_value=15,
        ),
        "reconnection_initial_delay_seconds": resolve_cfb_setting(
            env_int("CFB_RECONNECTION_INITIAL_DELAY", or_value=5),
            configured_value=5,
        ),
    }


def get_service_specific_config(service_name: str) -> Dict[str, Any]:
    """Get service-specific configuration overrides."""
    if service_name == "weather":
        from common.connectionconfig_helpers.config_loader import load_weather_config

        return load_weather_config()

    if service_name == "cfb":
        return build_cfb_config()

    ws_config = load_websocket_config()

    if service_name in ("kalshi", "deribit", "poly"):
        return build_websocket_config(ws_config)

    return dict()
