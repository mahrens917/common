"""Tests for memory monitor alert logger."""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from common.memory_monitor_helpers.alert_logger import AlertLogger


def test_init_stores_service_name():
    """Test that initialization stores service name."""
    logger = AlertLogger("test_service")
    assert logger.service_name == "test_service"


def test_log_alerts_critical_severity_uses_error():
    """Test that critical severity alerts use logger.error."""
    logger = AlertLogger("test_service")
    analysis: Dict[str, Any] = {"alerts": [{"severity": "critical", "message": "Critical memory issue"}]}

    with patch("common.memory_monitor_helpers.alert_logger.logger") as mock_logger:
        logger.log_alerts(analysis)
        mock_logger.error.assert_called_once_with("MEMORY_MONITOR[test_service]: Critical memory issue")
        mock_logger.warning.assert_not_called()
        mock_logger.info.assert_not_called()


def test_log_alerts_error_severity_uses_error():
    """Test that error severity alerts use logger.error."""
    logger = AlertLogger("test_service")
    analysis: Dict[str, Any] = {"alerts": [{"severity": "error", "message": "Error in memory"}]}

    with patch("common.memory_monitor_helpers.alert_logger.logger") as mock_logger:
        logger.log_alerts(analysis)
        mock_logger.error.assert_called_once_with("MEMORY_MONITOR[test_service]: Error in memory")
        mock_logger.warning.assert_not_called()
        mock_logger.info.assert_not_called()


def test_log_alerts_warning_severity_uses_warning():
    """Test that warning severity alerts use logger.warning."""
    logger = AlertLogger("test_service")
    analysis: Dict[str, Any] = {"alerts": [{"severity": "warning", "message": "Warning about memory"}]}

    with patch("common.memory_monitor_helpers.alert_logger.logger") as mock_logger:
        logger.log_alerts(analysis)
        mock_logger.warning.assert_called_once_with("MEMORY_MONITOR[test_service]: Warning about memory")
        mock_logger.error.assert_not_called()
        mock_logger.info.assert_not_called()


def test_log_alerts_info_severity_uses_info():
    """Test that info severity alerts use logger.info."""
    logger = AlertLogger("test_service")
    analysis: Dict[str, Any] = {"alerts": [{"severity": "info", "message": "Information message"}]}

    with patch("common.memory_monitor_helpers.alert_logger.logger") as mock_logger:
        logger.log_alerts(analysis)
        mock_logger.info.assert_called_once_with("MEMORY_MONITOR[test_service]: Information message")
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_not_called()


def test_log_alerts_unknown_severity_uses_info():
    """Test that unknown severity defaults to logger.info."""
    logger = AlertLogger("test_service")
    analysis: Dict[str, Any] = {"alerts": [{"severity": "debug", "message": "Debug message"}]}

    with patch("common.memory_monitor_helpers.alert_logger.logger") as mock_logger:
        logger.log_alerts(analysis)
        mock_logger.info.assert_called_once_with("MEMORY_MONITOR[test_service]: Debug message")
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_not_called()


def test_log_alerts_none_severity_uses_info():
    """Test that None severity defaults to logger.info."""
    logger = AlertLogger("test_service")
    analysis: Dict[str, Any] = {"alerts": [{"severity": None, "message": "No severity"}]}

    with patch("common.memory_monitor_helpers.alert_logger.logger") as mock_logger:
        logger.log_alerts(analysis)
        mock_logger.info.assert_called_once_with("MEMORY_MONITOR[test_service]: No severity")
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_not_called()


def test_log_alerts_empty_severity_uses_info():
    """Test that empty string severity defaults to logger.info."""
    logger = AlertLogger("test_service")
    analysis: Dict[str, Any] = {"alerts": [{"severity": "", "message": "Empty severity"}]}

    with patch("common.memory_monitor_helpers.alert_logger.logger") as mock_logger:
        logger.log_alerts(analysis)
        mock_logger.info.assert_called_once_with("MEMORY_MONITOR[test_service]: Empty severity")
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_not_called()


def test_log_alerts_missing_severity_uses_info():
    """Test that missing severity key defaults to logger.info."""
    logger = AlertLogger("test_service")
    analysis: Dict[str, Any] = {"alerts": [{"message": "No severity key"}]}

    with patch("common.memory_monitor_helpers.alert_logger.logger") as mock_logger:
        logger.log_alerts(analysis)
        mock_logger.info.assert_called_once_with("MEMORY_MONITOR[test_service]: No severity key")
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_not_called()


def test_log_alerts_with_empty_alerts_list():
    """Test that empty alerts list does not log anything."""
    logger = AlertLogger("test_service")
    analysis: Dict[str, Any] = {"alerts": []}

    with patch("common.memory_monitor_helpers.alert_logger.logger") as mock_logger:
        logger.log_alerts(analysis)
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_not_called()
        mock_logger.info.assert_not_called()


def test_log_alerts_with_none_alerts_defaults_to_empty_list():
    """Test that None alerts defaults to empty list and does not log anything."""
    logger = AlertLogger("test_service")
    analysis: Dict[str, Any] = {"alerts": None}

    with patch("common.memory_monitor_helpers.alert_logger.logger") as mock_logger:
        logger.log_alerts(analysis)
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_not_called()
        mock_logger.info.assert_not_called()


def test_log_alerts_with_missing_alerts_key():
    """Test that missing alerts key defaults to empty list."""
    logger = AlertLogger("test_service")
    analysis: Dict[str, Any] = {}

    with patch("common.memory_monitor_helpers.alert_logger.logger") as mock_logger:
        logger.log_alerts(analysis)
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_not_called()
        mock_logger.info.assert_not_called()


def test_message_format_includes_service_name():
    """Test that message format includes service name."""
    logger = AlertLogger("my_custom_service")
    analysis: Dict[str, Any] = {"alerts": [{"severity": "info", "message": "Test message"}]}

    with patch("common.memory_monitor_helpers.alert_logger.logger") as mock_logger:
        logger.log_alerts(analysis)
        mock_logger.info.assert_called_once_with("MEMORY_MONITOR[my_custom_service]: Test message")


def test_log_alerts_multiple_alerts_with_different_severities():
    """Test logging multiple alerts with different severities."""
    logger = AlertLogger("test_service")
    analysis: Dict[str, Any] = {
        "alerts": [
            {"severity": "critical", "message": "Critical alert"},
            {"severity": "warning", "message": "Warning alert"},
            {"severity": "info", "message": "Info alert"},
        ]
    }

    with patch("common.memory_monitor_helpers.alert_logger.logger") as mock_logger:
        logger.log_alerts(analysis)

        assert mock_logger.error.call_count == 1
        mock_logger.error.assert_called_with("MEMORY_MONITOR[test_service]: Critical alert")

        assert mock_logger.warning.call_count == 1
        mock_logger.warning.assert_called_with("MEMORY_MONITOR[test_service]: Warning alert")

        assert mock_logger.info.call_count == 1
        mock_logger.info.assert_called_with("MEMORY_MONITOR[test_service]: Info alert")


def test_log_alerts_preserves_alert_order():
    """Test that alerts are logged in the order they appear."""
    logger = AlertLogger("test_service")
    analysis: Dict[str, Any] = {
        "alerts": [
            {"severity": "info", "message": "First"},
            {"severity": "info", "message": "Second"},
            {"severity": "info", "message": "Third"},
        ]
    }

    with patch("common.memory_monitor_helpers.alert_logger.logger") as mock_logger:
        logger.log_alerts(analysis)

        assert mock_logger.info.call_count == 3
        calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert calls[0] == "MEMORY_MONITOR[test_service]: First"
        assert calls[1] == "MEMORY_MONITOR[test_service]: Second"
        assert calls[2] == "MEMORY_MONITOR[test_service]: Third"
