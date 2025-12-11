"""Tests for evaluation_cases module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from common.dawn_reset_service_helpers.dawn_calculator import DawnCalculator
from common.dawn_reset_service_helpers.field_reset_evaluator_helpers.evaluation_cases import (
    EvaluationCases,
    TimestampCrossingContext,
)


@pytest.fixture
def dawn_calculator():
    """Create a mock dawn calculator."""
    calc = MagicMock(spec=DawnCalculator)
    return calc


@pytest.fixture
def evaluation_cases(dawn_calculator):
    """Create evaluation cases instance."""
    return EvaluationCases(dawn_calculator)


def test_evaluate_first_run(evaluation_cases):
    """Test evaluate_first_run method."""
    latitude = 40.7128
    longitude = -74.0060
    current_timestamp = datetime(2023, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    last_dawn_reset = None
    field_name = "test_field"

    evaluation_cases._boundary_evaluator.evaluate_boundary = MagicMock(return_value=(True, current_timestamp))

    result, reset_time = evaluation_cases.evaluate_first_run(latitude, longitude, current_timestamp, last_dawn_reset, field_name)

    assert result is True
    assert reset_time == current_timestamp
    evaluation_cases._boundary_evaluator.evaluate_boundary.assert_called_once()


def test_evaluate_missing_timestamp(evaluation_cases):
    """Test evaluate_missing_timestamp method."""
    latitude = 40.7128
    longitude = -74.0060
    current_timestamp = datetime(2023, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    last_dawn_reset = datetime(2023, 1, 14, 10, 0, 0, tzinfo=timezone.utc)
    field_name = "test_field"
    timestamp_field = "updated_at"

    evaluation_cases._boundary_evaluator.evaluate_boundary = MagicMock(return_value=(True, current_timestamp))

    result, reset_time = evaluation_cases.evaluate_missing_timestamp(
        latitude, longitude, current_timestamp, last_dawn_reset, field_name, timestamp_field
    )

    assert result is True
    assert reset_time == current_timestamp
    evaluation_cases._boundary_evaluator.evaluate_boundary.assert_called_once()


def test_evaluate_null_timestamp(evaluation_cases):
    """Test evaluate_null_timestamp method."""
    latitude = 40.7128
    longitude = -74.0060
    current_timestamp = datetime(2023, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    last_dawn_reset = datetime(2023, 1, 14, 10, 0, 0, tzinfo=timezone.utc)
    field_name = "test_field"
    timestamp_field = "updated_at"

    evaluation_cases._boundary_evaluator.evaluate_boundary = MagicMock(return_value=(False, None))

    result, reset_time = evaluation_cases.evaluate_null_timestamp(
        latitude, longitude, current_timestamp, last_dawn_reset, field_name, timestamp_field
    )

    assert result is False
    assert reset_time is None
    evaluation_cases._boundary_evaluator.evaluate_boundary.assert_called_once()


def test_evaluate_timestamp_crossing_with_null_timestamp(evaluation_cases):
    """Test evaluate_timestamp_crossing when previous timestamp is None."""
    context = TimestampCrossingContext(
        latitude=40.7128,
        longitude=-74.0060,
        current_timestamp=datetime(2023, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        last_dawn_reset=datetime(2023, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
        field_name="test_field",
        timestamp_field="updated_at",
        previous_data={},
    )

    evaluation_cases._boundary_evaluator.evaluate_boundary = MagicMock(return_value=(True, context.current_timestamp))

    result, reset_time = evaluation_cases.evaluate_timestamp_crossing(context)

    assert result is True
    assert reset_time == context.current_timestamp


def test_evaluate_timestamp_crossing_with_valid_timestamp(evaluation_cases):
    """Test evaluate_timestamp_crossing when previous timestamp is valid."""
    previous_timestamp = datetime(2023, 1, 14, 15, 0, 0, tzinfo=timezone.utc)
    context = TimestampCrossingContext(
        latitude=40.7128,
        longitude=-74.0060,
        current_timestamp=datetime(2023, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        last_dawn_reset=datetime(2023, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
        field_name="test_field",
        timestamp_field="updated_at",
        previous_data={"updated_at": previous_timestamp},
    )

    evaluation_cases._timestamp_evaluator.evaluate = MagicMock(return_value=(True, context.current_timestamp))

    result, reset_time = evaluation_cases.evaluate_timestamp_crossing(context)

    assert result is True
    assert reset_time == context.current_timestamp
    evaluation_cases._timestamp_evaluator.evaluate.assert_called_once()
