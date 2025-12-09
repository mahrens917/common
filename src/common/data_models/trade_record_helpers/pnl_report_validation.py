"""Validation logic for PnLReport dataclass."""

from datetime import date
from typing import TYPE_CHECKING, Any

# Error messages
ERR_ZERO_ENTRY_COUNT = "Entry count must be positive: {value}"
ERR_ZERO_EXIT_COUNT = "Exit count must be positive: {value}"
ERR_NEGATIVE_PNL = "Total PnL cannot be negative: {value}"

if TYPE_CHECKING:
    from ..trade_record import PnLReport


def validate_pnl_report(report: "PnLReport") -> None:
    """Perform all validation checks on a PnL report."""
    _validate_date_fields(report.report_date, report.start_date, report.end_date)
    _validate_numeric_fields(report.total_trades, report.total_cost_cents, report.win_rate)


def _validate_date_fields(report_date: Any, start_date: Any, end_date: Any) -> None:
    """Validate date field integrity."""
    if not isinstance(report_date, date):
        raise TypeError("Report date must be a date object")
    if not isinstance(start_date, date):
        raise TypeError("Start date must be a date object")
    if not isinstance(end_date, date):
        raise TypeError("End date must be a date object")

    start_date_value = start_date
    end_date_value = end_date
    if start_date_value > end_date_value:
        raise ValueError("Start date cannot be after end date")


def _validate_numeric_fields(total_trades: int, total_cost_cents: int, win_rate: float) -> None:
    """Validate numeric field values."""
    if total_trades < 0:
        raise ValueError(f"Total trades cannot be negative: {total_trades}")

    if total_cost_cents < 0:
        raise ValueError(f"Total cost cannot be negative: {total_cost_cents}")

    if win_rate < 0.0 or win_rate > 1.0:
        raise TypeError(f"Win rate must be between 0.0 and 1.0: {win_rate}")


def _validate_breakdown_dicts(by_weather_station: Any, by_rule: Any) -> None:
    """Ensure breakdown dictionaries have the expected types."""
    if not isinstance(by_weather_station, dict):
        raise TypeError("Weather station breakdown must be a dict.")
    if not isinstance(by_rule, dict):
        raise TypeError("Rule breakdown must be a dict.")
