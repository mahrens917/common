"""Tests for PnL report validation."""

from __future__ import annotations

from datetime import date

import pytest

from src.common.data_models.trade_record_helpers.pnl_report_validation import (
    _validate_breakdown_dicts,
    _validate_date_fields,
    _validate_numeric_fields,
)


class TestValidateDateFields:
    """Tests for _validate_date_fields function."""

    def test_valid_dates(self) -> None:
        """Valid dates pass validation."""
        _validate_date_fields(
            report_date=date(2025, 1, 15),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

    def test_same_start_and_end_date(self) -> None:
        """Same start and end date is valid."""
        _validate_date_fields(
            report_date=date(2025, 1, 15),
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 15),
        )

    def test_invalid_report_date_type(self) -> None:
        """Non-date report_date raises TypeError."""
        with pytest.raises(TypeError, match="Report date must be a date object"):
            _validate_date_fields(
                report_date="2025-01-15",  # type: ignore[arg-type]
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
            )

    def test_invalid_start_date_type(self) -> None:
        """Non-date start_date raises TypeError."""
        with pytest.raises(TypeError, match="Start date must be a date object"):
            _validate_date_fields(
                report_date=date(2025, 1, 15),
                start_date="2025-01-01",  # type: ignore[arg-type]
                end_date=date(2025, 1, 31),
            )

    def test_invalid_end_date_type(self) -> None:
        """Non-date end_date raises TypeError."""
        with pytest.raises(TypeError, match="End date must be a date object"):
            _validate_date_fields(
                report_date=date(2025, 1, 15),
                start_date=date(2025, 1, 1),
                end_date="2025-01-31",  # type: ignore[arg-type]
            )

    def test_start_after_end_raises(self) -> None:
        """Start date after end date raises ValueError."""
        with pytest.raises(ValueError, match="Start date cannot be after end date"):
            _validate_date_fields(
                report_date=date(2025, 1, 15),
                start_date=date(2025, 2, 1),
                end_date=date(2025, 1, 31),
            )


class TestValidateNumericFields:
    """Tests for _validate_numeric_fields function."""

    def test_valid_values(self) -> None:
        """Valid numeric values pass validation."""
        _validate_numeric_fields(
            total_trades=10,
            total_cost_cents=1000,
            win_rate=0.65,
        )

    def test_zero_values_valid(self) -> None:
        """Zero values are valid."""
        _validate_numeric_fields(
            total_trades=0,
            total_cost_cents=0,
            win_rate=0.0,
        )

    def test_max_win_rate_valid(self) -> None:
        """Win rate of 1.0 is valid."""
        _validate_numeric_fields(
            total_trades=10,
            total_cost_cents=1000,
            win_rate=1.0,
        )

    def test_negative_trades_raises(self) -> None:
        """Negative total_trades raises ValueError."""
        with pytest.raises(ValueError, match="Total trades cannot be negative"):
            _validate_numeric_fields(
                total_trades=-1,
                total_cost_cents=1000,
                win_rate=0.5,
            )

    def test_negative_cost_raises(self) -> None:
        """Negative total_cost_cents raises ValueError."""
        with pytest.raises(ValueError, match="Total cost cannot be negative"):
            _validate_numeric_fields(
                total_trades=10,
                total_cost_cents=-100,
                win_rate=0.5,
            )

    def test_win_rate_below_zero_raises(self) -> None:
        """Win rate below 0 raises TypeError."""
        with pytest.raises(TypeError, match="Win rate must be between"):
            _validate_numeric_fields(
                total_trades=10,
                total_cost_cents=1000,
                win_rate=-0.1,
            )

    def test_win_rate_above_one_raises(self) -> None:
        """Win rate above 1 raises TypeError."""
        with pytest.raises(TypeError, match="Win rate must be between"):
            _validate_numeric_fields(
                total_trades=10,
                total_cost_cents=1000,
                win_rate=1.1,
            )


class TestValidateBreakdownDicts:
    """Tests for _validate_breakdown_dicts function."""

    def test_valid_dicts(self) -> None:
        """Valid dictionaries pass validation."""
        _validate_breakdown_dicts(
            by_weather_station={"KJFK": {}},
            by_rule={"rule1": {}},
        )

    def test_empty_dicts_valid(self) -> None:
        """Empty dictionaries are valid."""
        _validate_breakdown_dicts(
            by_weather_station={},
            by_rule={},
        )

    def test_invalid_weather_station_type(self) -> None:
        """Non-dict weather_station raises TypeError."""
        with pytest.raises(TypeError, match="Weather station breakdown must be"):
            _validate_breakdown_dicts(
                by_weather_station=["KJFK"],  # type: ignore[arg-type]
                by_rule={},
            )

    def test_invalid_rule_type(self) -> None:
        """Non-dict by_rule raises TypeError."""
        with pytest.raises(TypeError, match="Rule breakdown must be"):
            _validate_breakdown_dicts(
                by_weather_station={},
                by_rule="not a dict",  # type: ignore[arg-type]
            )
