"""Tests for trading day checker module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from common.dawn_reset_service_helpers.trading_day_checker import TradingDayChecker


class TestTradingDayCheckerInit:
    """Tests for TradingDayChecker initialization."""

    def test_initializes_with_dependencies(self) -> None:
        """Initializes with required dependencies."""
        dawn_calc = MagicMock()
        cache_mgr = MagicMock()
        logger = MagicMock()

        checker = TradingDayChecker(dawn_calculator=dawn_calc, cache_manager=cache_mgr, logger=logger)

        assert checker.dawn_calculator is dawn_calc
        assert checker.cache_manager is cache_mgr
        assert checker.logger is logger


class TestTradingDayCheckerIsNewTradingDay:
    """Tests for TradingDayChecker.is_new_trading_day."""

    def test_returns_cached_result_when_available(self) -> None:
        """Returns cached result when available."""
        dawn_calc = MagicMock()
        cache_mgr = MagicMock()
        cache_mgr.get_cache_key.return_value = "test_key"
        cache_mgr.get_cached_result.return_value = (
            True,
            datetime(2025, 1, 15, tzinfo=timezone.utc),
        )
        logger = MagicMock()

        checker = TradingDayChecker(dawn_calculator=dawn_calc, cache_manager=cache_mgr, logger=logger)
        prev = datetime(2025, 1, 14, 12, 0, 0, tzinfo=timezone.utc)
        curr = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        result = checker.is_new_trading_day(40.7128, -74.0060, prev, curr)

        assert result == (True, datetime(2025, 1, 15, tzinfo=timezone.utc))
        dawn_calc.is_new_trading_day.assert_not_called()

    def test_calculates_and_caches_when_not_cached(self) -> None:
        """Calculates new trading day and caches result."""
        dawn_calc = MagicMock()
        boundary = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        dawn_calc.is_new_trading_day.return_value = (True, boundary)
        cache_mgr = MagicMock()
        cache_mgr.get_cache_key.return_value = "test_key"
        cache_mgr.get_cached_result.return_value = None
        logger = MagicMock()

        checker = TradingDayChecker(dawn_calculator=dawn_calc, cache_manager=cache_mgr, logger=logger)
        prev = datetime(2025, 1, 14, 12, 0, 0, tzinfo=timezone.utc)
        curr = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        with patch("common.dawn_reset_service_helpers.trading_day_checker.calculate_dawn_utc") as mock_dawn:
            mock_dawn.return_value = datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)

            result = checker.is_new_trading_day(40.7128, -74.0060, prev, curr)

        assert result == (True, boundary)
        cache_mgr.cache_result.assert_called_once_with("test_key", (True, boundary))
        logger.log_dawn_check.assert_called_once()

    def test_uses_current_time_when_not_provided(self) -> None:
        """Uses current UTC time when current_timestamp not provided."""
        dawn_calc = MagicMock()
        boundary = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        dawn_calc.is_new_trading_day.return_value = (False, boundary)
        cache_mgr = MagicMock()
        cache_mgr.get_cache_key.return_value = "test_key"
        cache_mgr.get_cached_result.return_value = None
        logger = MagicMock()

        checker = TradingDayChecker(dawn_calculator=dawn_calc, cache_manager=cache_mgr, logger=logger)
        prev = datetime(2025, 1, 14, 12, 0, 0, tzinfo=timezone.utc)

        with patch("common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

            with patch("common.dawn_reset_service_helpers.trading_day_checker.calculate_dawn_utc") as mock_dawn:
                mock_dawn.return_value = datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)

                result = checker.is_new_trading_day(40.7128, -74.0060, prev)

        assert result == (False, boundary)

    def test_logs_dawn_check_context(self) -> None:
        """Logs dawn check context after calculation."""
        dawn_calc = MagicMock()
        boundary = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        dawn_calc.is_new_trading_day.return_value = (True, boundary)
        cache_mgr = MagicMock()
        cache_mgr.get_cache_key.return_value = "test_key"
        cache_mgr.get_cached_result.return_value = None
        logger = MagicMock()

        checker = TradingDayChecker(dawn_calculator=dawn_calc, cache_manager=cache_mgr, logger=logger)
        prev = datetime(2025, 1, 14, 12, 0, 0, tzinfo=timezone.utc)
        curr = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        with patch("common.dawn_reset_service_helpers.trading_day_checker.calculate_dawn_utc") as mock_dawn:
            mock_dawn.return_value = datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)

            checker.is_new_trading_day(40.7128, -74.0060, prev, curr)

        logger.log_dawn_check.assert_called_once()
        log_context = logger.log_dawn_check.call_args[0][0]
        assert log_context.latitude == 40.7128
        assert log_context.longitude == -74.0060
        assert log_context.is_new_day is True
        assert log_context.is_cached is False
