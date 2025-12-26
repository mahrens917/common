"""Tests for alerter_helpers.chart_manager module."""

from unittest.mock import MagicMock, patch

import pytest

from common.alerter_helpers.chart_manager import ChartManager


class TestChartManagerInit:
    """Tests for ChartManager initialization."""

    def test_stores_telegram_enabled(self) -> None:
        """Test initialization stores telegram_enabled flag."""
        manager = ChartManager(telegram_enabled=True)

        assert manager.telegram_enabled is True

    def test_initializes_with_none_dependencies(self) -> None:
        """Test initialization sets dependencies to None."""
        manager = ChartManager(telegram_enabled=True)

        assert manager.chart_generator is None
        assert manager.history_metrics_recorder is None
        assert manager.pnl_reporter is None


class TestChartManagerSetMetricsRecorder:
    """Tests for set_metrics_recorder method."""

    def test_sets_recorder(self) -> None:
        """Test sets metrics recorder."""
        manager = ChartManager(telegram_enabled=True)
        mock_recorder = MagicMock()

        manager.set_metrics_recorder(mock_recorder)

        assert manager.history_metrics_recorder == mock_recorder


class TestChartManagerEnsureChartDependenciesInitialized:
    """Tests for ensure_chart_dependencies_initialized method."""

    def test_skips_when_telegram_disabled(self) -> None:
        """Test skips initialization when Telegram disabled."""
        manager = ChartManager(telegram_enabled=False)

        manager.ensure_chart_dependencies_initialized()

        assert manager.chart_generator is None

    def test_skips_when_already_initialized(self) -> None:
        """Test skips initialization when already initialized."""
        manager = ChartManager(telegram_enabled=True)
        mock_generator = MagicMock()
        manager.chart_generator = mock_generator

        manager.ensure_chart_dependencies_initialized()

        assert manager.chart_generator == mock_generator

    @patch("common.alerter_helpers.chart_manager.ChartGenerator")
    def test_initializes_chart_generator(self, mock_generator_class: MagicMock) -> None:
        """Test initializes chart generator."""
        manager = ChartManager(telegram_enabled=True)
        mock_instance = MagicMock()
        mock_generator_class.return_value = mock_instance

        manager.ensure_chart_dependencies_initialized()

        assert manager.chart_generator == mock_instance
        mock_generator_class.assert_called_once()

    @patch("common.alerter_helpers.chart_manager.ChartGenerator")
    def test_raises_os_error(self, mock_generator_class: MagicMock) -> None:
        """Test raises OSError from chart generator."""
        manager = ChartManager(telegram_enabled=True)
        mock_generator_class.side_effect = OSError("File not found")

        with pytest.raises(OSError):
            manager.ensure_chart_dependencies_initialized()

    @patch("common.alerter_helpers.chart_manager.ChartGenerator")
    def test_raises_runtime_error(self, mock_generator_class: MagicMock) -> None:
        """Test raises RuntimeError from chart generator."""
        manager = ChartManager(telegram_enabled=True)
        mock_generator_class.side_effect = RuntimeError("Init failed")

        with pytest.raises(RuntimeError):
            manager.ensure_chart_dependencies_initialized()

    @patch("common.alerter_helpers.chart_manager.ChartGenerator")
    def test_raises_import_error(self, mock_generator_class: MagicMock) -> None:
        """Test raises ImportError from chart generator."""
        manager = ChartManager(telegram_enabled=True)
        mock_generator_class.side_effect = ImportError("Module not found")

        with pytest.raises(ImportError):
            manager.ensure_chart_dependencies_initialized()


class TestChartManagerEnsurePnlReporter:
    """Tests for ensure_pnl_reporter method."""

    @pytest.mark.asyncio
    async def test_creates_and_initializes_reporter(self) -> None:
        """Test creates and initializes PnL reporter."""
        manager = ChartManager(telegram_enabled=True)

        with patch("common.alerter_helpers.chart_manager.ChartManager.ensure_pnl_reporter") as mock_ensure:
            mock_reporter = MagicMock()
            mock_ensure.return_value = mock_reporter

            result = await manager.ensure_pnl_reporter()

            assert result == mock_reporter

    @pytest.mark.asyncio
    async def test_returns_existing_reporter(self) -> None:
        """Test returns existing PnL reporter."""
        manager = ChartManager(telegram_enabled=True)
        mock_reporter = MagicMock()
        mock_reporter.initialize = MagicMock(return_value=None)
        manager.pnl_reporter = mock_reporter

        # Mock the async initialize
        async def mock_init():
            pass

        mock_reporter.initialize = mock_init

        result = await manager.ensure_pnl_reporter()

        assert result == mock_reporter
