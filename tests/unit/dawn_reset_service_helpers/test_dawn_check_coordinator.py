"""Tests for dawn check coordinator module."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.common.dawn_reset_service_helpers.dawn_check_coordinator import DawnCheckCoordinator


class TestDawnCheckCoordinatorCheckNewTradingDay:
    """Tests for DawnCheckCoordinator.check_new_trading_day."""

    def test_returns_cached_result_when_available(self) -> None:
        """When cache has result, returns it without recalculating."""
        mock_calculator = MagicMock()
        mock_cache = MagicMock()
        mock_logger = MagicMock()

        cached_result = (True, datetime(2024, 12, 1, 6, 59, 0))
        mock_cache.get_cache_key.return_value = ("key1", "key2", "key3")
        mock_cache.get_cached_result.return_value = cached_result

        coordinator = DawnCheckCoordinator(mock_calculator, mock_cache, mock_logger)
        prev_ts = datetime(2024, 12, 1, 5, 0, 0)
        curr_ts = datetime(2024, 12, 1, 8, 0, 0)

        result = coordinator.check_new_trading_day(40.7128, -74.0060, prev_ts, curr_ts)

        assert result == cached_result
        mock_calculator.is_new_trading_day.assert_not_called()

    def test_calculates_and_caches_when_not_cached(self) -> None:
        """When no cache hit, calculates result and caches it."""
        mock_calculator = MagicMock()
        mock_cache = MagicMock()
        mock_logger = MagicMock()

        mock_cache.get_cache_key.return_value = ("key1", "key2", "key3")
        mock_cache.get_cached_result.return_value = None
        mock_calculator.is_new_trading_day.return_value = (True, datetime(2024, 12, 1, 6, 59, 0))

        coordinator = DawnCheckCoordinator(mock_calculator, mock_cache, mock_logger)
        prev_ts = datetime(2024, 12, 1, 5, 0, 0)
        curr_ts = datetime(2024, 12, 1, 8, 0, 0)

        result = coordinator.check_new_trading_day(40.7128, -74.0060, prev_ts, curr_ts)

        assert result[0] is True
        mock_calculator.is_new_trading_day.assert_called_once()
        mock_cache.cache_result.assert_called_once()

    def test_logs_dawn_check_when_calculating(self) -> None:
        """Logs the dawn check when not using cached result."""
        mock_calculator = MagicMock()
        mock_cache = MagicMock()
        mock_logger = MagicMock()

        mock_cache.get_cache_key.return_value = ("key1", "key2", "key3")
        mock_cache.get_cached_result.return_value = None
        mock_calculator.is_new_trading_day.return_value = (False, None)

        coordinator = DawnCheckCoordinator(mock_calculator, mock_cache, mock_logger)
        prev_ts = datetime(2024, 12, 1, 5, 0, 0)
        curr_ts = datetime(2024, 12, 1, 5, 30, 0)

        coordinator.check_new_trading_day(40.7128, -74.0060, prev_ts, curr_ts)

        mock_logger.log_dawn_check.assert_called_once()
        call_kwargs = mock_logger.log_dawn_check.call_args
        assert call_kwargs[1]["is_cached"] is False


class TestDawnCheckCoordinatorInit:
    """Tests for DawnCheckCoordinator initialization."""

    def test_init_stores_dependencies(self) -> None:
        """Initialization stores all dependencies."""
        mock_calculator = MagicMock()
        mock_cache = MagicMock()
        mock_logger = MagicMock()

        coordinator = DawnCheckCoordinator(mock_calculator, mock_cache, mock_logger)

        assert coordinator.dawn_calculator is mock_calculator
        assert coordinator.cache_manager is mock_cache
        assert coordinator.logger is mock_logger
