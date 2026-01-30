"""Tests for midnight_reset_service_helpers field_reset_applicator module."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from common.midnight_reset_service_helpers.field_reset_applicator import FieldResetApplicator


class StubEvaluator:
    """Stub evaluator for testing."""

    DAILY_RESET_FIELDS = {"t_bid", "t_ask", "max_temp_f"}

    def __init__(self, should_reset: bool):
        self._should_reset = should_reset

    def should_reset_field(self, *args, **kwargs):
        return self._should_reset


class TestFieldResetApplicatorInit:
    """Tests for FieldResetApplicator initialization."""

    def test_creates_with_evaluator(self) -> None:
        """Test creating applicator with evaluator."""
        evaluator = StubEvaluator(False)
        applicator = FieldResetApplicator(evaluator)
        assert applicator._reset_evaluator is evaluator


class TestApplyFieldResets:
    """Tests for apply_field_resets method."""

    def test_returns_unchanged_for_non_daily_field(self) -> None:
        """Test that non-daily fields are returned unchanged."""
        evaluator = StubEvaluator(False)
        applicator = FieldResetApplicator(evaluator)

        result, was_reset = applicator.apply_field_resets("non_daily_field", "value", {}, 0, 0)
        assert result == "value"
        assert was_reset is False

    def test_clears_field_on_reset_for_clear_fields(self) -> None:
        """Test clearing field when reset is needed for CLEAR_ON_RESET_FIELDS."""
        evaluator = StubEvaluator(True)
        applicator = FieldResetApplicator(evaluator)

        with patch("common.midnight_reset_service_helpers.field_reset_applicator.logger"):
            result, was_reset = applicator.apply_field_resets("t_bid", 50.0, {}, 0, 0)

        assert result is None
        assert was_reset is True

    def test_clears_t_ask_on_reset(self) -> None:
        """Test clearing t_ask field when reset is needed."""
        evaluator = StubEvaluator(True)
        applicator = FieldResetApplicator(evaluator)

        with patch("common.midnight_reset_service_helpers.field_reset_applicator.logger"):
            result, was_reset = applicator.apply_field_resets("t_ask", 55.0, {}, 0, 0)

        assert result is None
        assert was_reset is True

    def test_returns_current_on_reset_for_non_clear_fields(self) -> None:
        """Test returning current value when reset is needed for non-clear fields."""
        evaluator = StubEvaluator(True)
        applicator = FieldResetApplicator(evaluator)

        with patch("common.midnight_reset_service_helpers.field_reset_applicator.logger"):
            result, was_reset = applicator.apply_field_resets("max_temp_f", 72.0, {}, 0, 0)

        assert result == 72.0
        assert was_reset is True

    def test_preserves_previous_when_no_reset_and_current_is_none(self) -> None:
        """Test preserving previous value when no reset and current is None."""
        evaluator = StubEvaluator(False)
        applicator = FieldResetApplicator(evaluator)

        with patch("common.midnight_reset_service_helpers.field_reset_applicator.logger"):
            result, was_reset = applicator.apply_field_resets("max_temp_f", None, {"max_temp_f": 68.0}, 0, 0)

        assert result == 68.0
        assert was_reset is False

    def test_uses_current_when_no_reset_and_field_not_in_previous(self) -> None:
        """Test using current value when no reset and field not in previous data."""
        evaluator = StubEvaluator(False)
        applicator = FieldResetApplicator(evaluator)

        with patch("common.midnight_reset_service_helpers.field_reset_applicator.logger"):
            result, was_reset = applicator.apply_field_resets("max_temp_f", 72.0, {}, 0, 0)

        assert result == 72.0
        assert was_reset is False


class TestClearOnResetFields:
    """Tests for CLEAR_ON_RESET_FIELDS constant."""

    def test_contains_expected_fields(self) -> None:
        """Test that CLEAR_ON_RESET_FIELDS contains expected fields."""
        expected = {"weather_explanation", "last_rule_applied", "t_bid", "t_ask"}
        assert FieldResetApplicator.CLEAR_ON_RESET_FIELDS == expected
