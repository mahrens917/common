"""Tests for telegram_network_backoff_manager module."""

import time
from unittest.mock import patch

import pytest

from common.alerter_helpers.telegram_network_backoff_manager import TelegramNetworkBackoffManager


class TestTelegramNetworkBackoffManager:
    """Tests for TelegramNetworkBackoffManager class."""

    def test_init(self) -> None:
        """Test TelegramNetworkBackoffManager initialization."""
        manager = TelegramNetworkBackoffManager(30)

        assert manager.telegram_timeout_seconds == 30
        assert manager._block_until is None
        assert manager._reason is None
        assert manager._logged is False

    def test_should_skip_operation_no_backoff(self) -> None:
        """Test should_skip_operation returns False when no backoff active."""
        manager = TelegramNetworkBackoffManager(30)

        result = manager.should_skip_operation("sendMessage")

        assert result is False

    def test_should_skip_operation_during_backoff(self) -> None:
        """Test should_skip_operation returns True during backoff."""
        manager = TelegramNetworkBackoffManager(30)
        manager._block_until = time.time() + 60
        manager._reason = "Test error"

        result = manager.should_skip_operation("sendMessage")

        assert result is True
        assert manager._logged is True

    def test_should_skip_operation_backoff_expired(self) -> None:
        """Test should_skip_operation clears backoff when expired."""
        manager = TelegramNetworkBackoffManager(30)
        manager._block_until = time.time() - 1
        manager._reason = "Test error"

        result = manager.should_skip_operation("sendMessage")

        assert result is False
        assert manager._block_until is None
        assert manager._reason is None

    def test_should_skip_operation_logs_once(self) -> None:
        """Test should_skip_operation only logs once per backoff period."""
        manager = TelegramNetworkBackoffManager(30)
        manager._block_until = time.time() + 60
        manager._reason = "Test error"

        manager.should_skip_operation("sendMessage")
        assert manager._logged is True

        manager.should_skip_operation("sendMessage")
        assert manager._logged is True

    def test_should_skip_operation_unknown_reason(self) -> None:
        """Test should_skip_operation with no reason set."""
        manager = TelegramNetworkBackoffManager(30)
        manager._block_until = time.time() + 60
        manager._reason = None

        result = manager.should_skip_operation("sendMessage")

        assert result is True

    def test_record_failure(self) -> None:
        """Test record_failure sets backoff state."""
        manager = TelegramNetworkBackoffManager(30)
        exception = RuntimeError("Connection failed")

        with patch("common.alerter_helpers.telegram_network_backoff_manager.time.time", return_value=1000.0):
            manager.record_failure(exception)

        assert manager._block_until == 1060.0
        assert manager._reason == "Connection failed"
        assert manager._logged is False

    def test_record_failure_uses_timeout_for_cooldown(self) -> None:
        """Test record_failure uses timeout * 2 for cooldown."""
        manager = TelegramNetworkBackoffManager(60)
        exception = RuntimeError("Error")

        with patch("common.alerter_helpers.telegram_network_backoff_manager.time.time", return_value=1000.0):
            manager.record_failure(exception)

        assert manager._block_until == 1120.0

    def test_record_failure_minimum_cooldown(self) -> None:
        """Test record_failure has minimum 60s cooldown."""
        manager = TelegramNetworkBackoffManager(10)
        exception = RuntimeError("Error")

        with patch("common.alerter_helpers.telegram_network_backoff_manager.time.time", return_value=1000.0):
            manager.record_failure(exception)

        assert manager._block_until == 1060.0

    def test_record_failure_empty_message(self) -> None:
        """Test record_failure with empty exception message."""
        manager = TelegramNetworkBackoffManager(30)
        exception = RuntimeError("")

        manager.record_failure(exception)

        assert manager._reason == "RuntimeError"

    def test_clear_backoff(self) -> None:
        """Test clear_backoff resets state."""
        manager = TelegramNetworkBackoffManager(30)
        manager._block_until = time.time() + 60
        manager._reason = "Test error"
        manager._logged = True

        manager.clear_backoff()

        assert manager._block_until is None
        assert manager._reason is None
        assert manager._logged is False

    def test_clear_backoff_when_not_blocked(self) -> None:
        """Test clear_backoff does nothing when not blocked."""
        manager = TelegramNetworkBackoffManager(30)

        manager.clear_backoff()

        assert manager._block_until is None
