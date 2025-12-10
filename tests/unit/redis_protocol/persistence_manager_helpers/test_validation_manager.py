"""Tests for validation manager module."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from common.redis_protocol.persistence_manager_helpers.validation_manager import (
    ValidationManager,
    check_aof_enabled,
    check_rdb_enabled,
    is_properly_configured,
)


class TestCheckAofEnabled:
    """Tests for check_aof_enabled function."""

    def test_returns_true_when_enabled(self) -> None:
        """Returns True when AOF is enabled."""
        status = {"aof_enabled": True}

        result = check_aof_enabled(status)

        assert result is True

    def test_returns_false_when_disabled(self) -> None:
        """Returns False when AOF is disabled."""
        status = {"aof_enabled": False}

        result = check_aof_enabled(status)

        assert result is False

    def test_returns_false_when_missing(self) -> None:
        """Returns False when aof_enabled not in status."""
        status = {}

        result = check_aof_enabled(status)

        assert result is False


class TestCheckRdbEnabled:
    """Tests for check_rdb_enabled function."""

    def test_returns_true_when_enabled(self) -> None:
        """Returns True when RDB is enabled."""
        status = {"rdb_enabled": True}

        result = check_rdb_enabled(status)

        assert result is True

    def test_returns_false_when_disabled(self) -> None:
        """Returns False when RDB is disabled."""
        status = {"rdb_enabled": False}

        result = check_rdb_enabled(status)

        assert result is False

    def test_returns_false_when_missing(self) -> None:
        """Returns False when rdb_enabled not in status."""
        status = {}

        result = check_rdb_enabled(status)

        assert result is False


class TestIsProperlyConfigured:
    """Tests for is_properly_configured function."""

    def test_returns_true_when_configured(self) -> None:
        """Returns True when properly configured."""
        status = {"persistence_properly_configured": True}

        result = is_properly_configured(status)

        assert result is True

    def test_returns_false_when_not_configured(self) -> None:
        """Returns False when not properly configured."""
        status = {"persistence_properly_configured": False}

        result = is_properly_configured(status)

        assert result is False

    def test_returns_false_when_missing(self) -> None:
        """Returns False when key not in status."""
        status = {}

        result = is_properly_configured(status)

        assert result is False


class TestValidateStatus:
    """Tests for validate_status method."""

    def test_returns_false_with_error_in_status(self) -> None:
        """Returns (False, message) when status has error."""
        manager = ValidationManager()
        status = {"error": "Connection failed"}

        valid, message = manager.validate_status(status)

        assert valid is False
        assert "Error checking persistence" in message
        assert "Connection failed" in message

    def test_returns_false_when_aof_disabled(self) -> None:
        """Returns (False, message) when AOF disabled."""
        manager = ValidationManager()
        status = {
            "aof_enabled": False,
            "rdb_enabled": True,
            "data_directory": "/tmp",
        }

        valid, message = manager.validate_status(status)

        assert valid is False
        assert "AOF persistence is disabled" in message

    def test_returns_false_when_rdb_disabled(self) -> None:
        """Returns (False, message) when RDB disabled."""
        manager = ValidationManager()
        status = {
            "aof_enabled": True,
            "rdb_enabled": False,
            "data_directory": "/tmp",
        }

        valid, message = manager.validate_status(status)

        assert valid is False
        assert "RDB persistence is disabled" in message

    def test_returns_false_when_both_disabled(self) -> None:
        """Returns (False, message) when both disabled."""
        manager = ValidationManager()
        status = {
            "aof_enabled": False,
            "rdb_enabled": False,
            "data_directory": "/tmp",
        }

        valid, message = manager.validate_status(status)

        assert valid is False
        assert "AOF persistence is disabled" in message
        assert "RDB persistence is disabled" in message

    def test_returns_true_when_properly_configured(self) -> None:
        """Returns (True, message) when properly configured."""
        manager = ValidationManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            status = {
                "aof_enabled": True,
                "rdb_enabled": True,
                "data_directory": tmpdir,
            }

            valid, message = manager.validate_status(status)

            assert valid is True
            assert "properly configured" in message


class TestValidateDataDirectory:
    """Tests for _validate_data_directory method."""

    def test_returns_false_when_directory_not_exists(self) -> None:
        """Returns (False, message) when directory does not exist."""
        manager = ValidationManager()

        valid, message = manager._validate_data_directory("/nonexistent/path")

        assert valid is False
        assert "does not exist" in message

    def test_returns_false_when_path_is_file(self) -> None:
        """Returns (False, message) when path is a file."""
        manager = ValidationManager()
        with tempfile.NamedTemporaryFile() as tmpfile:
            valid, message = manager._validate_data_directory(tmpfile.name)

            assert valid is False
            assert "not a directory" in message

    def test_returns_true_for_valid_directory(self) -> None:
        """Returns (True, message) for valid writable directory."""
        manager = ValidationManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            valid, message = manager._validate_data_directory(tmpdir)

            assert valid is True
            assert "valid" in message.lower()

    def test_handles_system_directory_without_write_access(self) -> None:
        """Handles system directories without write access."""
        manager = ValidationManager()
        # Code checks for paths starting with /var/, /usr/, /opt/ (with trailing slash)
        # So we need to use subdirectories like /var/lib, /usr/local
        system_dirs = ["/var/lib", "/var/log", "/usr/local", "/usr/share"]

        found_unwritable_system_dir = False
        for sys_dir in system_dirs:
            if os.path.isdir(sys_dir) and not os.access(sys_dir, os.W_OK):
                # Found an unwritable system directory - test the behavior
                valid, message = manager._validate_data_directory(sys_dir)
                # System directories return True with warning
                assert valid is True
                assert "system directory" in message.lower()
                found_unwritable_system_dir = True
                break

        # If no unwritable system dirs found (e.g. running as root),
        # skip this test scenario - it's environment-dependent
        if not found_unwritable_system_dir:
            pytest.skip("No unwritable system directories found for testing")
