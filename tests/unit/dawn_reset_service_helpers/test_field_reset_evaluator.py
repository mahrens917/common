"""Tests for field reset evaluator module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.common.dawn_reset_service_helpers.field_reset_evaluator import FieldResetEvaluator


class TestFieldResetEvaluatorInit:
    """Tests for FieldResetEvaluator initialization."""

    def test_initializes_with_dependencies(self) -> None:
        """Initializes with all required dependencies."""
        dawn_calc = MagicMock()
        timestamp_resolver = MagicMock()

        evaluator = FieldResetEvaluator(
            dawn_calculator=dawn_calc, timestamp_resolver=timestamp_resolver
        )

        assert evaluator.dawn_calculator is dawn_calc
        assert evaluator.timestamp_resolver is timestamp_resolver

    def test_creates_evaluation_cases(self) -> None:
        """Creates evaluation cases helper."""
        dawn_calc = MagicMock()
        timestamp_resolver = MagicMock()

        evaluator = FieldResetEvaluator(
            dawn_calculator=dawn_calc, timestamp_resolver=timestamp_resolver
        )

        assert evaluator._evaluation_cases is not None

    def test_creates_boundary_checker(self) -> None:
        """Creates boundary checker helper."""
        dawn_calc = MagicMock()
        timestamp_resolver = MagicMock()

        evaluator = FieldResetEvaluator(
            dawn_calculator=dawn_calc, timestamp_resolver=timestamp_resolver
        )

        assert evaluator._boundary_checker is not None


class TestFieldResetEvaluatorShouldResetField:
    """Tests for FieldResetEvaluator.should_reset_field."""

    def test_returns_false_for_non_reset_field(self) -> None:
        """Returns False for field not in DAILY_RESET_FIELDS."""
        dawn_calc = MagicMock()
        timestamp_resolver = MagicMock()
        timestamp_resolver.DAILY_RESET_FIELDS = ["max_temp_f", "min_temp_f"]

        evaluator = FieldResetEvaluator(
            dawn_calculator=dawn_calc, timestamp_resolver=timestamp_resolver
        )

        result, boundary = evaluator.should_reset_field(
            field_name="some_other_field",
            latitude=40.7128,
            longitude=-74.0060,
            previous_data={},
        )

        assert result is False
        assert boundary is None

    def test_uses_current_time_when_not_provided(self) -> None:
        """Uses current UTC time when not provided."""
        dawn_calc = MagicMock()
        timestamp_resolver = MagicMock()
        timestamp_resolver.DAILY_RESET_FIELDS = ["max_temp_f"]
        timestamp_resolver.get_last_dawn_reset_timestamp.return_value = None

        evaluator = FieldResetEvaluator(
            dawn_calculator=dawn_calc, timestamp_resolver=timestamp_resolver
        )
        boundary = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        evaluator._evaluation_cases = MagicMock()
        evaluator._evaluation_cases.evaluate_first_run.return_value = (True, boundary)

        with patch("src.common.time_utils.get_current_utc") as mock_time:
            mock_time.return_value = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

            result, returned_boundary = evaluator.should_reset_field(
                field_name="max_temp_f",
                latitude=40.7128,
                longitude=-74.0060,
                previous_data={},
            )

        assert result is True
        assert returned_boundary == boundary

    def test_evaluates_first_run_for_empty_previous_data(self) -> None:
        """Evaluates first run case for empty previous data."""
        dawn_calc = MagicMock()
        timestamp_resolver = MagicMock()
        timestamp_resolver.DAILY_RESET_FIELDS = ["max_temp_f"]
        timestamp_resolver.get_last_dawn_reset_timestamp.return_value = None

        evaluator = FieldResetEvaluator(
            dawn_calculator=dawn_calc, timestamp_resolver=timestamp_resolver
        )
        boundary = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        evaluator._evaluation_cases = MagicMock()
        evaluator._evaluation_cases.evaluate_first_run.return_value = (True, boundary)
        current = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)

        result, returned_boundary = evaluator.should_reset_field(
            field_name="max_temp_f",
            latitude=40.7128,
            longitude=-74.0060,
            previous_data={},
            current_timestamp=current,
        )

        assert result is True
        assert returned_boundary == boundary
        evaluator._evaluation_cases.evaluate_first_run.assert_called_once()

    def test_evaluates_missing_timestamp_field(self) -> None:
        """Evaluates missing timestamp case when timestamp field missing."""
        dawn_calc = MagicMock()
        timestamp_resolver = MagicMock()
        timestamp_resolver.DAILY_RESET_FIELDS = ["max_temp_f"]
        timestamp_resolver.get_last_dawn_reset_timestamp.return_value = None
        timestamp_resolver.get_timestamp_field_for_reset_field.return_value = "max_temp_f_timestamp"

        evaluator = FieldResetEvaluator(
            dawn_calculator=dawn_calc, timestamp_resolver=timestamp_resolver
        )
        boundary = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        evaluator._evaluation_cases = MagicMock()
        evaluator._evaluation_cases.evaluate_missing_timestamp.return_value = (True, boundary)
        current = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
        previous_data = {"other_field": "value"}  # Missing timestamp field

        result, returned_boundary = evaluator.should_reset_field(
            field_name="max_temp_f",
            latitude=40.7128,
            longitude=-74.0060,
            previous_data=previous_data,
            current_timestamp=current,
        )

        assert result is True
        evaluator._evaluation_cases.evaluate_missing_timestamp.assert_called_once()

    def test_evaluates_timestamp_crossing(self) -> None:
        """Evaluates timestamp crossing case when timestamp field present."""
        dawn_calc = MagicMock()
        timestamp_resolver = MagicMock()
        timestamp_resolver.DAILY_RESET_FIELDS = ["max_temp_f"]
        timestamp_resolver.get_last_dawn_reset_timestamp.return_value = None
        timestamp_resolver.get_timestamp_field_for_reset_field.return_value = "max_temp_f_timestamp"

        evaluator = FieldResetEvaluator(
            dawn_calculator=dawn_calc, timestamp_resolver=timestamp_resolver
        )
        boundary = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        evaluator._evaluation_cases = MagicMock()
        evaluator._evaluation_cases.evaluate_timestamp_crossing.return_value = (True, boundary)
        current = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
        previous_data = {"max_temp_f_timestamp": "2025-01-14T12:00:00Z"}

        result, returned_boundary = evaluator.should_reset_field(
            field_name="max_temp_f",
            latitude=40.7128,
            longitude=-74.0060,
            previous_data=previous_data,
            current_timestamp=current,
        )

        assert result is True
        evaluator._evaluation_cases.evaluate_timestamp_crossing.assert_called_once()

    def test_returns_false_when_no_reset_needed(self) -> None:
        """Returns False when no reset needed."""
        dawn_calc = MagicMock()
        timestamp_resolver = MagicMock()
        timestamp_resolver.DAILY_RESET_FIELDS = ["max_temp_f"]
        timestamp_resolver.get_last_dawn_reset_timestamp.return_value = datetime(
            2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc
        )
        timestamp_resolver.get_timestamp_field_for_reset_field.return_value = "max_temp_f_timestamp"

        evaluator = FieldResetEvaluator(
            dawn_calculator=dawn_calc, timestamp_resolver=timestamp_resolver
        )
        evaluator._evaluation_cases = MagicMock()
        evaluator._evaluation_cases.evaluate_timestamp_crossing.return_value = (False, None)
        current = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
        previous_data = {"max_temp_f_timestamp": "2025-01-15T12:00:00Z"}

        result, boundary = evaluator.should_reset_field(
            field_name="max_temp_f",
            latitude=40.7128,
            longitude=-74.0060,
            previous_data=previous_data,
            current_timestamp=current,
        )

        assert result is False
        assert boundary is None

    def test_passes_correct_context_to_timestamp_crossing(self) -> None:
        """Passes correct context to timestamp crossing evaluation."""
        dawn_calc = MagicMock()
        timestamp_resolver = MagicMock()
        timestamp_resolver.DAILY_RESET_FIELDS = ["max_temp_f"]
        timestamp_resolver.get_last_dawn_reset_timestamp.return_value = None
        timestamp_resolver.get_timestamp_field_for_reset_field.return_value = "max_temp_f_timestamp"

        evaluator = FieldResetEvaluator(
            dawn_calculator=dawn_calc, timestamp_resolver=timestamp_resolver
        )
        evaluator._evaluation_cases = MagicMock()
        evaluator._evaluation_cases.evaluate_timestamp_crossing.return_value = (False, None)
        current = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
        previous_data = {"max_temp_f_timestamp": "2025-01-15T12:00:00Z"}

        evaluator.should_reset_field(
            field_name="max_temp_f",
            latitude=40.7128,
            longitude=-74.0060,
            previous_data=previous_data,
            current_timestamp=current,
        )

        call_args = evaluator._evaluation_cases.evaluate_timestamp_crossing.call_args[0][0]
        assert call_args.latitude == 40.7128
        assert call_args.longitude == -74.0060
        assert call_args.current_timestamp == current
        assert call_args.field_name == "max_temp_f"
        assert call_args.timestamp_field == "max_temp_f_timestamp"
