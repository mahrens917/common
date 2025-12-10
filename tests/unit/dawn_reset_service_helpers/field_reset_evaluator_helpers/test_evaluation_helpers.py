"""Tests for evaluation helpers module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from common.dawn_reset_service_helpers.field_reset_evaluator_helpers.evaluation_helpers import (
    BoundaryEvaluator,
    TimestampCrossingEvaluator,
    _BaseEvaluator,
)
from common.exceptions import DataError


class TestBaseEvaluator:
    """Tests for _BaseEvaluator class."""

    def test_initializes_with_dependencies(self) -> None:
        """Initializes with dawn calculator and boundary checker."""
        dawn_calc = MagicMock()
        boundary_check = MagicMock()

        evaluator = _BaseEvaluator(dawn_calculator=dawn_calc, boundary_checker=boundary_check)

        assert evaluator.dawn_calculator is dawn_calc
        assert evaluator.boundary_checker is boundary_check


class TestBoundaryEvaluator:
    """Tests for BoundaryEvaluator class."""

    def test_returns_false_when_already_processed(self) -> None:
        """Returns false when boundary already processed."""
        dawn_calc = MagicMock()
        boundary = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        dawn_calc.resolve_latest_dawn_boundary.return_value = boundary
        boundary_check = MagicMock()
        boundary_check.already_processed.return_value = True

        evaluator = BoundaryEvaluator(dawn_calculator=dawn_calc, boundary_checker=boundary_check)
        last_reset = datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
        current = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)

        result, returned_boundary = evaluator.evaluate_boundary(
            40.7128, -74.0060, current, last_reset, "Test log", "test_context"
        )

        assert result is False
        assert returned_boundary == boundary
        boundary_check.log_skip.assert_called_once()

    def test_returns_true_when_not_processed(self) -> None:
        """Returns true when boundary not already processed."""
        dawn_calc = MagicMock()
        boundary = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        dawn_calc.resolve_latest_dawn_boundary.return_value = boundary
        boundary_check = MagicMock()
        boundary_check.already_processed.return_value = False

        evaluator = BoundaryEvaluator(dawn_calculator=dawn_calc, boundary_checker=boundary_check)
        current = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)

        result, returned_boundary = evaluator.evaluate_boundary(
            40.7128, -74.0060, current, None, "Test log", "test_context"
        )

        assert result is True
        assert returned_boundary == boundary


class TestTimestampCrossingEvaluator:
    """Tests for TimestampCrossingEvaluator class."""

    def test_returns_false_when_no_previous_timestamp(self) -> None:
        """Returns false when previous timestamp is None."""
        dawn_calc = MagicMock()
        boundary_check = MagicMock()

        evaluator = TimestampCrossingEvaluator(
            dawn_calculator=dawn_calc, boundary_checker=boundary_check
        )
        current = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)

        result, boundary = evaluator.evaluate(40.7128, -74.0060, current, None, "max_temp_f", None)

        assert result is False
        assert boundary is None

    def test_returns_false_when_not_new_day(self) -> None:
        """Returns false when not a new trading day."""
        dawn_calc = MagicMock()
        dawn_calc.is_new_trading_day.return_value = (False, None)
        boundary_check = MagicMock()

        evaluator = TimestampCrossingEvaluator(
            dawn_calculator=dawn_calc, boundary_checker=boundary_check
        )
        current = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)

        result, boundary = evaluator.evaluate(
            40.7128, -74.0060, current, None, "max_temp_f", "2025-01-15T12:00:00Z"
        )

        assert result is False
        assert boundary is None

    def test_returns_false_when_already_processed(self) -> None:
        """Returns false when already processed."""
        dawn_calc = MagicMock()
        boundary = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        dawn_calc.is_new_trading_day.return_value = (True, boundary)
        boundary_check = MagicMock()
        boundary_check.already_processed.return_value = True

        evaluator = TimestampCrossingEvaluator(
            dawn_calculator=dawn_calc, boundary_checker=boundary_check
        )
        current = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
        last_reset = datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)

        result, returned_boundary = evaluator.evaluate(
            40.7128, -74.0060, current, last_reset, "max_temp_f", "2025-01-15T10:00:00Z"
        )

        assert result is False
        assert returned_boundary == boundary

    def test_returns_true_when_new_day_and_not_processed(self) -> None:
        """Returns true when new trading day and not already processed."""
        dawn_calc = MagicMock()
        boundary = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        dawn_calc.is_new_trading_day.return_value = (True, boundary)
        boundary_check = MagicMock()
        boundary_check.already_processed.return_value = False

        evaluator = TimestampCrossingEvaluator(
            dawn_calculator=dawn_calc, boundary_checker=boundary_check
        )
        current = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)

        result, returned_boundary = evaluator.evaluate(
            40.7128, -74.0060, current, None, "max_temp_f", "2025-01-14T10:00:00Z"
        )

        assert result is True
        assert returned_boundary == boundary

    def test_raises_data_error_on_invalid_timestamp(self) -> None:
        """Raises DataError on invalid timestamp parsing."""
        dawn_calc = MagicMock()
        dawn_calc.is_new_trading_day.side_effect = ValueError("Invalid date")
        boundary_check = MagicMock()

        evaluator = TimestampCrossingEvaluator(
            dawn_calculator=dawn_calc, boundary_checker=boundary_check
        )
        current = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)

        with pytest.raises(DataError) as exc_info:
            evaluator.evaluate(
                40.7128, -74.0060, current, None, "max_temp_f", "not-a-valid-timestamp"
            )

        assert "Failed to parse timestamp" in str(exc_info.value)
