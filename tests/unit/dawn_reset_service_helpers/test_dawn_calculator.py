"""Tests for dawn calculator module."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from common.dawn_reset_service_helpers.dawn_calculator import DawnCalculator


class TestDawnCalculatorIsNewTradingDay:
    """Tests for DawnCalculator.is_new_trading_day."""

    def test_is_new_trading_day_before_dawn(self) -> None:
        """Returns False when not crossing dawn boundary."""
        mock_calculate_dawn = MagicMock(return_value=datetime(2024, 12, 1, 7, 0, 0))
        calculator = DawnCalculator(calculate_dawn_fn=mock_calculate_dawn)

        prev_ts = datetime(2024, 12, 1, 5, 0, 0)
        curr_ts = datetime(2024, 12, 1, 5, 30, 0)

        is_new, dawn = calculator.is_new_trading_day(40.7128, -74.0060, prev_ts, curr_ts)

        assert is_new is False
        assert dawn is None

    def test_is_new_trading_day_crossing_dawn(self) -> None:
        """Returns True when crossing dawn reset boundary."""
        mock_calculate_dawn = MagicMock(return_value=datetime(2024, 12, 1, 7, 0, 0))
        calculator = DawnCalculator(calculate_dawn_fn=mock_calculate_dawn)

        prev_ts = datetime(2024, 12, 1, 6, 30, 0)
        curr_ts = datetime(2024, 12, 1, 7, 30, 0)

        is_new, dawn = calculator.is_new_trading_day(40.7128, -74.0060, prev_ts, curr_ts)

        assert is_new is True
        assert dawn is not None
        assert dawn == datetime(2024, 12, 1, 6, 59, 0)

    def test_is_new_trading_day_uses_current_utc_if_none(self) -> None:
        """Uses current UTC time when current_timestamp is None."""
        mock_calculate_dawn = MagicMock(return_value=datetime(2024, 12, 1, 7, 0, 0))
        calculator = DawnCalculator(calculate_dawn_fn=mock_calculate_dawn)

        prev_ts = datetime(2024, 12, 1, 5, 0, 0)

        with patch("common.dawn_reset_service_helpers.dawn_calculator.get_current_utc") as mock_now:
            mock_now.return_value = datetime(2024, 12, 1, 5, 30, 0)

            is_new, dawn = calculator.is_new_trading_day(40.7128, -74.0060, prev_ts)

            mock_now.assert_called_once()

    def test_is_new_trading_day_crossing_previous_day_dawn(self) -> None:
        """Returns True when crossing previous day's dawn boundary."""

        def mock_calculate_dawn(lat, lon, ts):
            if ts.day == 1:
                return datetime(2024, 12, 1, 7, 0, 0)
            return datetime(2024, 11, 30, 7, 0, 0)

        calculator = DawnCalculator(calculate_dawn_fn=mock_calculate_dawn)

        prev_ts = datetime(2024, 11, 30, 6, 30, 0)
        curr_ts = datetime(2024, 11, 30, 7, 30, 0)

        is_new, dawn = calculator.is_new_trading_day(40.7128, -74.0060, prev_ts, curr_ts)

        assert is_new is True


class TestDawnCalculatorResolveLatestDawnBoundary:
    """Tests for DawnCalculator.resolve_latest_dawn_boundary."""

    def test_resolve_latest_dawn_after_reset(self) -> None:
        """Returns today's dawn when after reset time."""
        mock_calculate_dawn = MagicMock(return_value=datetime(2024, 12, 1, 7, 0, 0))
        calculator = DawnCalculator(calculate_dawn_fn=mock_calculate_dawn)

        curr_ts = datetime(2024, 12, 1, 8, 0, 0)

        result = calculator.resolve_latest_dawn_boundary(40.7128, -74.0060, curr_ts)

        assert result == datetime(2024, 12, 1, 6, 59, 0)

    def test_resolve_latest_dawn_before_reset(self) -> None:
        """Returns previous day's dawn when before reset time."""

        def mock_calculate_dawn(lat, lon, ts):
            if ts.day == 1:
                return datetime(2024, 12, 1, 7, 0, 0)
            return datetime(2024, 11, 30, 7, 0, 0)

        calculator = DawnCalculator(calculate_dawn_fn=mock_calculate_dawn)

        curr_ts = datetime(2024, 12, 1, 5, 0, 0)

        result = calculator.resolve_latest_dawn_boundary(40.7128, -74.0060, curr_ts)

        assert result == datetime(2024, 11, 30, 6, 59, 0)

    def test_resolve_latest_dawn_uses_current_utc_if_none(self) -> None:
        """Uses current UTC when timestamp is None."""
        mock_calculate_dawn = MagicMock(return_value=datetime(2024, 12, 1, 7, 0, 0))
        calculator = DawnCalculator(calculate_dawn_fn=mock_calculate_dawn)

        with patch("common.dawn_reset_service_helpers.dawn_calculator.get_current_utc") as mock_now:
            mock_now.return_value = datetime(2024, 12, 1, 8, 0, 0)

            result = calculator.resolve_latest_dawn_boundary(40.7128, -74.0060)

            mock_now.assert_called_once()


class TestDawnCalculatorInit:
    """Tests for DawnCalculator initialization."""

    def test_init_with_custom_function(self) -> None:
        """Can initialize with custom dawn calculation function."""
        custom_fn = MagicMock()
        calculator = DawnCalculator(calculate_dawn_fn=custom_fn)

        assert calculator._calculate_dawn_utc is custom_fn

    def test_init_with_none_uses_default(self) -> None:
        """Uses default function when None is passed."""
        calculator = DawnCalculator(calculate_dawn_fn=None)

        assert calculator._calculate_dawn_utc is not None
