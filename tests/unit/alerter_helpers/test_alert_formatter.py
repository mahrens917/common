"""Tests for alert_formatter module."""

import time

import pytest

from common.alerter_helpers.alert_formatter import AlertFormatter
from common.alerting import Alert, AlertSeverity


class TestAlertFormatter:
    """Tests for AlertFormatter class."""

    def test_format_info_alert(self) -> None:
        """Test formatting INFO alert."""
        formatter = AlertFormatter()
        alert = Alert(
            message="Test message",
            severity=AlertSeverity.INFO,
            timestamp=time.time(),
            alert_type="test",
        )

        result = formatter.format_telegram_message(alert)

        assert result == " Test message"

    def test_format_warning_alert(self) -> None:
        """Test formatting WARNING alert."""
        formatter = AlertFormatter()
        alert = Alert(
            message="Warning message",
            severity=AlertSeverity.WARNING,
            timestamp=time.time(),
            alert_type="test",
        )

        result = formatter.format_telegram_message(alert)

        assert "Warning message" in result

    def test_format_critical_alert(self) -> None:
        """Test formatting CRITICAL alert."""
        formatter = AlertFormatter()
        alert = Alert(
            message="Critical error",
            severity=AlertSeverity.CRITICAL,
            timestamp=time.time(),
            alert_type="test",
        )

        result = formatter.format_telegram_message(alert)

        assert "Critical error" in result

    def test_format_alert_with_details(self) -> None:
        """Test formatting alert with details."""
        formatter = AlertFormatter()
        alert = Alert(
            message="Test message",
            severity=AlertSeverity.INFO,
            timestamp=time.time(),
            alert_type="test",
            details={"key1": "value1", "key2": "value2"},
        )

        result = formatter.format_telegram_message(alert)

        assert "Details:" in result
        assert "key1: value1" in result
        assert "key2: value2" in result

    def test_message_already_has_checkmark_emoji(self) -> None:
        """Test message starting with checkmark emoji is not modified."""
        formatter = AlertFormatter()
        alert = Alert(
            message="✅ Trade executed",
            severity=AlertSeverity.INFO,
            timestamp=time.time(),
            alert_type="test",
        )

        result = formatter.format_telegram_message(alert)

        assert result == "✅ Trade executed"

    def test_message_already_has_alert_emoji(self) -> None:
        """Test message starting with alert emoji is not modified."""
        formatter = AlertFormatter()
        alert = Alert(
            message="🚨 Critical alert",
            severity=AlertSeverity.CRITICAL,
            timestamp=time.time(),
            alert_type="test",
        )

        result = formatter.format_telegram_message(alert)

        assert result == "🚨 Critical alert"

    def test_message_already_has_warning_emoji(self) -> None:
        """Test message starting with warning emoji is not modified."""
        formatter = AlertFormatter()
        alert = Alert(
            message="⚠️ Warning issued",
            severity=AlertSeverity.WARNING,
            timestamp=time.time(),
            alert_type="test",
        )

        result = formatter.format_telegram_message(alert)

        assert result == "⚠️ Warning issued"

    def test_message_with_existing_emoji_no_details_added(self) -> None:
        """Test that details are not added when message has existing emoji."""
        formatter = AlertFormatter()
        alert = Alert(
            message="✅ Success!",
            severity=AlertSeverity.INFO,
            timestamp=time.time(),
            alert_type="test",
            details={"key": "value"},
        )

        result = formatter.format_telegram_message(alert)

        assert "Details:" not in result

    def test_empty_message(self) -> None:
        """Test formatting empty message."""
        formatter = AlertFormatter()
        alert = Alert(
            message="",
            severity=AlertSeverity.INFO,
            timestamp=time.time(),
            alert_type="test",
        )

        result = formatter.format_telegram_message(alert)

        assert result == " "
