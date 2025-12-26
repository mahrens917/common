"""Tests for chart_generator_helpers.chart_file_manager module."""

from unittest.mock import MagicMock

import pytest

from common.chart_generator_helpers.chart_file_manager import ChartFileManager


class TestChartFileManager:
    """Tests for ChartFileManager class."""

    def test_init_with_default_os(self) -> None:
        """Test initialization with default os module."""
        manager = ChartFileManager()

        assert manager._os is not None

    def test_init_with_custom_os(self) -> None:
        """Test initialization with custom os module."""
        mock_os = MagicMock()
        manager = ChartFileManager(os_module=mock_os)

        assert manager._os == mock_os


class TestCleanupChartFiles:
    """Tests for cleanup_chart_files method."""

    def test_cleans_up_existing_files(self) -> None:
        """Test cleans up existing files."""
        mock_os = MagicMock()
        mock_os.path.exists.return_value = True
        manager = ChartFileManager(os_module=mock_os)

        manager.cleanup_chart_files(["/tmp/chart1.png", "/tmp/chart2.png"])

        assert mock_os.unlink.call_count == 2

    def test_raises_on_missing_file(self) -> None:
        """Test raises RuntimeError when file not found."""
        mock_os = MagicMock()
        mock_os.path.exists.return_value = False
        manager = ChartFileManager(os_module=mock_os)

        with pytest.raises(RuntimeError, match="Chart file not found"):
            manager.cleanup_chart_files(["/tmp/missing.png"])

    def test_raises_on_unlink_error(self) -> None:
        """Test raises RuntimeError when unlink fails."""
        mock_os = MagicMock()
        mock_os.path.exists.return_value = True
        mock_os.unlink.side_effect = OSError("Permission denied")
        manager = ChartFileManager(os_module=mock_os)

        with pytest.raises(RuntimeError, match="Failed to clean up"):
            manager.cleanup_chart_files(["/tmp/chart.png"])

    def test_empty_list(self) -> None:
        """Test handles empty list."""
        mock_os = MagicMock()
        manager = ChartFileManager(os_module=mock_os)

        manager.cleanup_chart_files([])

        mock_os.unlink.assert_not_called()


class TestCleanupSingleChartFile:
    """Tests for cleanup_single_chart_file method."""

    def test_cleans_up_existing_file(self) -> None:
        """Test cleans up existing file."""
        mock_os = MagicMock()
        mock_os.path.exists.return_value = True
        manager = ChartFileManager(os_module=mock_os)

        manager.cleanup_single_chart_file("/tmp/chart.png")

        mock_os.unlink.assert_called_once_with("/tmp/chart.png")

    def test_raises_on_missing_file(self) -> None:
        """Test raises RuntimeError when file not found."""
        mock_os = MagicMock()
        mock_os.path.exists.return_value = False
        manager = ChartFileManager(os_module=mock_os)

        with pytest.raises(RuntimeError, match="Chart file not found"):
            manager.cleanup_single_chart_file("/tmp/missing.png")

    def test_raises_on_unlink_error(self) -> None:
        """Test raises RuntimeError when unlink fails."""
        mock_os = MagicMock()
        mock_os.path.exists.return_value = True
        mock_os.unlink.side_effect = OSError("Permission denied")
        manager = ChartFileManager(os_module=mock_os)

        with pytest.raises(RuntimeError, match="Failed to clean up"):
            manager.cleanup_single_chart_file("/tmp/chart.png")
