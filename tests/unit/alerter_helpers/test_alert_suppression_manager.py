"""Tests for alerter_helpers.alert_suppression_manager module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from common.alerter_helpers.alert_suppression_manager import (
    AlertSuppressionManager,
    _get_runtime_directory,
    _get_shutdown_flag_path,
)


class TestGetRuntimeDirectory:
    """Tests for _get_runtime_directory function."""

    def test_returns_temp_dir_by_default(self) -> None:
        """Test returns tempdir when no env override."""
        with patch.dict(os.environ, {}, clear=True):
            if "MONITOR_RUNTIME_DIR" in os.environ:
                del os.environ["MONITOR_RUNTIME_DIR"]
            result = _get_runtime_directory()

        assert result == Path(tempfile.gettempdir())

    def test_uses_env_override(self) -> None:
        """Test uses MONITOR_RUNTIME_DIR when set."""
        with patch.dict(os.environ, {"MONITOR_RUNTIME_DIR": "/custom/path"}):
            result = _get_runtime_directory()

        assert result == Path("/custom/path")


class TestGetShutdownFlagPath:
    """Tests for _get_shutdown_flag_path function."""

    def test_returns_path_with_marker_name(self) -> None:
        """Test returns path with shutdown marker name."""
        with patch(
            "common.alerter_helpers.alert_suppression_manager._get_runtime_directory",
            return_value=Path("/tmp"),
        ):
            result = _get_shutdown_flag_path()

        assert result == Path("/tmp/monitor_shutdown_in_progress")


class TestAlertSuppressionManager:
    """Tests for AlertSuppressionManager class."""

    def test_should_suppress_returns_false_when_not_shutting_down(self) -> None:
        """Test returns False when not shutting down."""
        manager = AlertSuppressionManager()

        with patch.object(manager, "is_shutdown_in_progress", return_value=False):
            result = manager.should_suppress_alert("process_status")

        assert result is False

    def test_should_suppress_returns_true_for_suppressed_type(self) -> None:
        """Test returns True for suppressed alert type during shutdown."""
        manager = AlertSuppressionManager()

        with patch.object(manager, "is_shutdown_in_progress", return_value=True):
            result = manager.should_suppress_alert("process_status")

        assert result is True

    def test_should_suppress_returns_false_for_non_suppressed_type(self) -> None:
        """Test returns False for non-suppressed alert type during shutdown."""
        manager = AlertSuppressionManager()

        with patch.object(manager, "is_shutdown_in_progress", return_value=True):
            result = manager.should_suppress_alert("critical_error")

        assert result is False

    def test_suppressed_types(self) -> None:
        """Test all suppressed types are suppressed during shutdown."""
        manager = AlertSuppressionManager()

        with patch.object(manager, "is_shutdown_in_progress", return_value=True):
            for alert_type in manager.SHUTDOWN_SUPPRESSED_TYPES:
                assert manager.should_suppress_alert(alert_type) is True

    def test_is_shutdown_via_env_var_true(self) -> None:
        """Test detects shutdown via env var."""
        manager = AlertSuppressionManager()

        with patch.dict(os.environ, {"SHUTDOWN_IN_PROGRESS": "true"}):
            result = manager.is_shutdown_in_progress()

        assert result is True

    def test_is_shutdown_via_env_var_false(self) -> None:
        """Test returns False when env var is false."""
        manager = AlertSuppressionManager()

        with patch.dict(os.environ, {"SHUTDOWN_IN_PROGRESS": "false"}, clear=True):
            with patch("common.alerter_helpers.alert_suppression_manager._get_shutdown_flag_path") as mock_path:
                mock_path.return_value.exists.return_value = False
                result = manager.is_shutdown_in_progress()

        assert result is False

    def test_is_shutdown_via_flag_file(self) -> None:
        """Test detects shutdown via flag file."""
        manager = AlertSuppressionManager()

        with patch.dict(os.environ, {}, clear=True):
            if "SHUTDOWN_IN_PROGRESS" in os.environ:
                del os.environ["SHUTDOWN_IN_PROGRESS"]
            with patch("common.alerter_helpers.alert_suppression_manager._get_shutdown_flag_path") as mock_path:
                mock_path.return_value.exists.return_value = True
                result = manager.is_shutdown_in_progress()

        assert result is True

    def test_is_shutdown_no_env_no_file(self) -> None:
        """Test returns False when no env var and no flag file."""
        manager = AlertSuppressionManager()

        with patch.dict(os.environ, {}, clear=True):
            if "SHUTDOWN_IN_PROGRESS" in os.environ:
                del os.environ["SHUTDOWN_IN_PROGRESS"]
            with patch("common.alerter_helpers.alert_suppression_manager._get_shutdown_flag_path") as mock_path:
                mock_path.return_value.exists.return_value = False
                result = manager.is_shutdown_in_progress()

        assert result is False
