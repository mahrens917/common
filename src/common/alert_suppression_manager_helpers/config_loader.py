"""Configuration loading and validation for alert suppression.

Delegates to load_config() for JSON loading, provides domain-specific validation.
"""

from pathlib import Path
from typing import Any, Dict, Set

from common.config_loader import load_config
from common.exceptions import ConfigurationError

from .alert_evaluator import SuppressionRule
from .suppression_tracker import AlertType

# Error messages
ERR_CONFIG_NOT_FOUND = "Alert suppression config not found at {config_path}"
ERR_MISSING_ALERT_SUPPRESSION_SECTION = "monitor_config.json missing 'alert_suppression' section"


class AlertSuppressionConfigurationError(RuntimeError):
    """Raised when alert suppression configuration is invalid."""


def load_suppression_config(config_path: str = "config/monitor_config.json") -> Dict[str, Any]:
    """
    Load alert suppression configuration and fail if mandatory fields are missing.

    Delegates to canonical load_config() for JSON loading with consistent error handling.

    Args:
        config_path: Path to configuration file

    Returns:
        Alert suppression configuration dictionary

    Raises:
        FileNotFoundError: If config file not found
        ValueError: If required configuration fields are missing
        TypeError: If configuration structure is invalid
        ConfigurationError: If JSON is invalid
    """
    # Extract filename from path for load_config
    config_file = Path(config_path).name

    try:
        config = load_config(config_file)
    except FileNotFoundError as exc:
        raise FileNotFoundError(ERR_CONFIG_NOT_FOUND.format(config_path=config_path)) from exc
    except ConfigurationError as exc:
        raise ConfigurationError(f"Invalid JSON in {config_path}") from exc

    if "alert_suppression" not in config:
        raise ConfigurationError(ERR_MISSING_ALERT_SUPPRESSION_SECTION)

    alert_config = config["alert_suppression"]
    _validate_root_keys(alert_config)
    _validate_suppression_rules(alert_config["suppression_rules"])

    return alert_config


def _validate_root_keys(alert_config: Dict[str, Any]) -> None:
    """Validate required root-level keys in alert_suppression section."""
    required_root_keys = {"enabled", "grace_period_seconds", "suppression_rules"}
    missing_root = required_root_keys.difference(alert_config)
    if missing_root:
        raise ValueError(f"alert_suppression missing keys: {sorted(missing_root)}")


def _validate_suppression_rules(rules: Any) -> None:
    """Validate suppression_rules section structure."""
    if not isinstance(rules, dict):
        raise TypeError("alert_suppression.suppression_rules must be a mapping")

    required_rule_keys = {"during_reconnection", "service_type_mapping"}
    missing_rule = required_rule_keys.difference(rules)
    if missing_rule:
        raise ValueError(f"suppression_rules missing keys: {sorted(missing_rule)}")

    _validate_during_reconnection(rules["during_reconnection"])
    _validate_service_type_mapping(rules["service_type_mapping"])


def _validate_during_reconnection(during_reconnection: Any) -> None:
    """Validate during_reconnection list."""
    if not isinstance(during_reconnection, list):
        raise TypeError("suppression_rules.during_reconnection must be a list")
    if not during_reconnection:
        raise TypeError("suppression_rules.during_reconnection must be a non-empty list")


def _validate_service_type_mapping(service_type_mapping: Any) -> None:
    """Validate service_type_mapping dictionary."""
    if not isinstance(service_type_mapping, dict):
        raise TypeError("suppression_rules.service_type_mapping must be a mapping")
    if not service_type_mapping:
        raise TypeError("suppression_rules.service_type_mapping must be a non-empty mapping")


def build_suppression_rule_from_config(config: Dict[str, Any]) -> SuppressionRule:
    """
    Build SuppressionRule from loaded configuration.

    Args:
        config: Loaded alert suppression configuration

    Returns:
        Configured SuppressionRule instance

    Raises:
        AlertSuppressionConfigurationError: If alert types are invalid
    """
    requested_alert_types = config["suppression_rules"]["during_reconnection"]
    suppressed_alert_types = _convert_alert_types(requested_alert_types)

    return SuppressionRule(
        enabled=config["enabled"],
        grace_period_seconds=config["grace_period_seconds"],
        suppressed_alert_types=suppressed_alert_types,
    )


def _convert_alert_types(alert_type_strings: list[str]) -> Set[AlertType]:
    """
    Convert string alert types to AlertType enum.

    Args:
        alert_type_strings: List of alert type strings

    Returns:
        Set of AlertType enum values

    Raises:
        AlertSuppressionConfigurationError: If any alert type is invalid
    """
    valid_alert_types = {alert_type.value: alert_type for alert_type in AlertType}
    invalid_alert_types = [alert_type_str for alert_type_str in alert_type_strings if alert_type_str not in valid_alert_types]

    if invalid_alert_types:
        raise AlertSuppressionConfigurationError("Unknown alert types in monitor_config: " + ", ".join(sorted(invalid_alert_types)))

    return {valid_alert_types[alert_type_str] for alert_type_str in alert_type_strings}
