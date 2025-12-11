"""Tests for alert suppression config loader."""

import pytest

from common.alert_suppression_manager_helpers.config_loader import (
    AlertSuppressionConfigurationError,
    build_suppression_rule_from_config,
    load_suppression_config,
)
from common.alert_suppression_manager_helpers.suppression_tracker import AlertType
from common.exceptions import ConfigurationError


def test_load_suppression_config_success(monkeypatch):
    """Test successful config loading."""
    mock_config = {
        "alert_suppression": {
            "enabled": True,
            "grace_period_seconds": 30,
            "suppression_rules": {
                "during_reconnection": ["connection_error"],
                "service_type_mapping": {"kalshi": "websocket"},
            },
        }
    }
    monkeypatch.setattr(
        "common.alert_suppression_manager_helpers.config_loader.load_config",
        lambda x: mock_config,
    )

    config = load_suppression_config()

    assert config["enabled"] is True
    assert config["grace_period_seconds"] == 30


def test_load_suppression_config_file_not_found(monkeypatch):
    """Test config loading when file not found."""

    def raise_file_not_found(x):
        raise FileNotFoundError("Config not found")

    monkeypatch.setattr(
        "common.alert_suppression_manager_helpers.config_loader.load_config",
        raise_file_not_found,
    )

    with pytest.raises(FileNotFoundError, match="Alert suppression config not found"):
        load_suppression_config()


def test_load_suppression_config_invalid_json(monkeypatch):
    """Test config loading with invalid JSON."""

    def raise_config_error(x):
        raise ConfigurationError("Invalid JSON")

    monkeypatch.setattr("common.alert_suppression_manager_helpers.config_loader.load_config", raise_config_error)

    with pytest.raises(ConfigurationError, match="Invalid JSON"):
        load_suppression_config()


def test_load_suppression_config_missing_alert_suppression_section(monkeypatch):
    """Test config loading when alert_suppression section is missing."""
    mock_config = {"other_config": {}}
    monkeypatch.setattr(
        "common.alert_suppression_manager_helpers.config_loader.load_config",
        lambda x: mock_config,
    )

    with pytest.raises(ConfigurationError, match="missing 'alert_suppression' section"):
        load_suppression_config()


def test_load_suppression_config_missing_root_keys(monkeypatch):
    """Test config validation with missing root keys."""
    mock_config = {
        "alert_suppression": {
            "enabled": True,
        }
    }
    monkeypatch.setattr(
        "common.alert_suppression_manager_helpers.config_loader.load_config",
        lambda x: mock_config,
    )

    with pytest.raises(ValueError, match="alert_suppression missing keys"):
        load_suppression_config()


def test_load_suppression_config_suppression_rules_not_mapping(monkeypatch):
    """Test validation when suppression_rules is not a mapping."""
    mock_config = {
        "alert_suppression": {
            "enabled": True,
            "grace_period_seconds": 30,
            "suppression_rules": [],
        }
    }
    monkeypatch.setattr(
        "common.alert_suppression_manager_helpers.config_loader.load_config",
        lambda x: mock_config,
    )

    with pytest.raises(TypeError, match="must be a mapping"):
        load_suppression_config()


def test_load_suppression_config_missing_rule_keys(monkeypatch):
    """Test validation when suppression_rules is missing required keys."""
    mock_config = {
        "alert_suppression": {
            "enabled": True,
            "grace_period_seconds": 30,
            "suppression_rules": {
                "during_reconnection": ["connection_error"],
            },
        }
    }
    monkeypatch.setattr(
        "common.alert_suppression_manager_helpers.config_loader.load_config",
        lambda x: mock_config,
    )

    with pytest.raises(ValueError, match="suppression_rules missing keys"):
        load_suppression_config()


def test_load_suppression_config_during_reconnection_not_list(monkeypatch):
    """Test validation when during_reconnection is not a list."""
    mock_config = {
        "alert_suppression": {
            "enabled": True,
            "grace_period_seconds": 30,
            "suppression_rules": {
                "during_reconnection": "connection_error",
                "service_type_mapping": {},
            },
        }
    }
    monkeypatch.setattr(
        "common.alert_suppression_manager_helpers.config_loader.load_config",
        lambda x: mock_config,
    )

    with pytest.raises(TypeError, match="must be a list"):
        load_suppression_config()


def test_load_suppression_config_during_reconnection_empty(monkeypatch):
    """Test validation when during_reconnection is empty."""
    mock_config = {
        "alert_suppression": {
            "enabled": True,
            "grace_period_seconds": 30,
            "suppression_rules": {
                "during_reconnection": [],
                "service_type_mapping": {"kalshi": "websocket"},
            },
        }
    }
    monkeypatch.setattr(
        "common.alert_suppression_manager_helpers.config_loader.load_config",
        lambda x: mock_config,
    )

    with pytest.raises(TypeError, match="must be a non-empty list"):
        load_suppression_config()


def test_load_suppression_config_service_type_mapping_not_mapping(monkeypatch):
    """Test validation when service_type_mapping is not a mapping."""
    mock_config = {
        "alert_suppression": {
            "enabled": True,
            "grace_period_seconds": 30,
            "suppression_rules": {
                "during_reconnection": ["connection_error"],
                "service_type_mapping": [],
            },
        }
    }
    monkeypatch.setattr(
        "common.alert_suppression_manager_helpers.config_loader.load_config",
        lambda x: mock_config,
    )

    with pytest.raises(TypeError, match="must be a mapping"):
        load_suppression_config()


def test_load_suppression_config_service_type_mapping_empty(monkeypatch):
    """Test validation when service_type_mapping is empty."""
    mock_config = {
        "alert_suppression": {
            "enabled": True,
            "grace_period_seconds": 30,
            "suppression_rules": {
                "during_reconnection": ["connection_error"],
                "service_type_mapping": {},
            },
        }
    }
    monkeypatch.setattr(
        "common.alert_suppression_manager_helpers.config_loader.load_config",
        lambda x: mock_config,
    )

    with pytest.raises(TypeError, match="must be a non-empty mapping"):
        load_suppression_config()


def test_build_suppression_rule_from_config_success():
    """Test building suppression rule from config."""
    config = {
        "enabled": True,
        "grace_period_seconds": 45,
        "suppression_rules": {
            "during_reconnection": ["connection_error", "timeout"],
            "service_type_mapping": {"kalshi": "websocket"},
        },
    }

    rule = build_suppression_rule_from_config(config)

    assert rule.enabled is True
    assert rule.grace_period_seconds == 45
    assert AlertType.CONNECTION_ERROR in rule.suppressed_alert_types
    assert AlertType.TIMEOUT in rule.suppressed_alert_types


def test_build_suppression_rule_from_config_invalid_alert_type():
    """Test building rule with invalid alert type."""
    config = {
        "enabled": True,
        "grace_period_seconds": 30,
        "suppression_rules": {
            "during_reconnection": ["invalid_alert_type"],
            "service_type_mapping": {"kalshi": "websocket"},
        },
    }

    with pytest.raises(AlertSuppressionConfigurationError, match="Unknown alert types"):
        build_suppression_rule_from_config(config)


def test_build_suppression_rule_from_config_multiple_invalid_alert_types():
    """Test building rule with multiple invalid alert types."""
    config = {
        "enabled": False,
        "grace_period_seconds": 60,
        "suppression_rules": {
            "during_reconnection": ["bad_type_1", "connection_error", "bad_type_2"],
            "service_type_mapping": {"kalshi": "websocket"},
        },
    }

    with pytest.raises(AlertSuppressionConfigurationError) as exc_info:
        build_suppression_rule_from_config(config)

    assert "bad_type_1" in str(exc_info.value)
    assert "bad_type_2" in str(exc_info.value)
