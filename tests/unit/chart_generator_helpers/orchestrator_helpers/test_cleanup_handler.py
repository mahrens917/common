"""Tests for chart_generator_helpers.orchestrator_helpers.cleanup_handler module."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from common.chart_generator_helpers.orchestrator_helpers.cleanup_handler import (
    cleanup_chart_files,
)

# Test constants
TEST_EXPECTED_CLEANUP_CALL_COUNT = 2


class TestCleanupChartFiles:
    """Tests for cleanup_chart_files function."""

    def test_removes_existing_files(self) -> None:
        """Test removes existing chart files."""
        with patch("os.path.exists", return_value=True) as mock_exists:
            with patch("os.unlink") as mock_unlink:
                cleanup_chart_files(["/path/chart1.png", "/path/chart2.png"])

                assert mock_exists.call_count == 2
                assert mock_unlink.call_count == 2
                mock_unlink.assert_any_call("/path/chart1.png")
                mock_unlink.assert_any_call("/path/chart2.png")

    def test_skips_nonexistent_files(self) -> None:
        """Test skips files that don't exist."""
        with patch("os.path.exists", return_value=False) as mock_exists:
            with patch("os.unlink") as mock_unlink:
                cleanup_chart_files(["/path/missing.png"])

                mock_exists.assert_called_once_with("/path/missing.png")
                mock_unlink.assert_not_called()

    def test_handles_empty_list(self) -> None:
        """Test handles empty file list."""
        with patch("os.path.exists") as mock_exists:
            with patch("os.unlink") as mock_unlink:
                cleanup_chart_files([])

                mock_exists.assert_not_called()
                mock_unlink.assert_not_called()

    def test_handles_oserror_gracefully(self) -> None:
        """Test handles OSError during cleanup gracefully."""
        with patch("os.path.exists", return_value=True):
            with patch("os.unlink", side_effect=OSError("Permission denied")):
                # Should not raise
                cleanup_chart_files(["/path/locked.png"])

    def test_logs_warning_on_oserror(self, caplog) -> None:
        """Test logs warning when cleanup fails."""
        with caplog.at_level(logging.WARNING, logger="src.monitor.chart_generator"):
            with patch("os.path.exists", return_value=True):
                with patch("os.unlink", side_effect=OSError("Permission denied")):
                    cleanup_chart_files(["/path/locked.png"])

                    assert "Unable to clean up weather chart" in caplog.text
                    assert "/path/locked.png" in caplog.text

    def test_continues_after_error(self) -> None:
        """Test continues cleaning other files after error."""
        call_count = 0

        def unlink_side_effect(path):
            nonlocal call_count
            call_count += 1
            if "chart1" in path:
                raise OSError("Permission denied")

        with patch("os.path.exists", return_value=True):
            with patch("os.unlink", side_effect=unlink_side_effect):
                cleanup_chart_files(["/path/chart1.png", "/path/chart2.png"])

                assert call_count == TEST_EXPECTED_CLEANUP_CALL_COUNT

    def test_mixed_existing_and_missing(self) -> None:
        """Test handles mix of existing and missing files."""

        def exists_side_effect(path):
            return "exists" in path

        with patch("os.path.exists", side_effect=exists_side_effect):
            with patch("os.unlink") as mock_unlink:
                cleanup_chart_files(
                    [
                        "/path/exists1.png",
                        "/path/missing.png",
                        "/path/exists2.png",
                    ]
                )

                assert mock_unlink.call_count == 2
                mock_unlink.assert_any_call("/path/exists1.png")
                mock_unlink.assert_any_call("/path/exists2.png")
