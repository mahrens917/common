"""Tests for boundary checker module."""

from datetime import datetime, timezone
from unittest.mock import patch

from common.dawn_reset_service_helpers.field_reset_evaluator_helpers.boundary_checker import (
    BoundaryChecker,
    _format_timestamp,
)


class TestFormatTimestamp:
    """Tests for _format_timestamp function."""

    def test_formats_datetime_value(self) -> None:
        """Formats datetime value to ISO format."""
        dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        result = _format_timestamp(dt)

        assert result == "2025-01-15T12:00:00+00:00"

    def test_returns_missing_for_none(self) -> None:
        """Returns '<missing>' for None value."""
        result = _format_timestamp(None)

        assert result == "<missing>"


class TestBoundaryCheckerAlreadyProcessed:
    """Tests for BoundaryChecker.already_processed."""

    def test_returns_false_when_boundary_is_none(self) -> None:
        """Returns False when boundary is None."""
        last_reset = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        result = BoundaryChecker.already_processed(last_reset, None)

        assert result is False

    def test_returns_false_when_last_reset_is_none(self) -> None:
        """Returns False when last_dawn_reset is None."""
        boundary = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        result = BoundaryChecker.already_processed(None, boundary)

        assert result is False

    def test_returns_true_when_reset_equals_boundary(self) -> None:
        """Returns True when last_dawn_reset equals boundary."""
        boundary = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        last_reset = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        result = BoundaryChecker.already_processed(last_reset, boundary)

        assert result is True

    def test_returns_true_when_reset_after_boundary(self) -> None:
        """Returns True when last_dawn_reset is after boundary."""
        boundary = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        last_reset = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)

        result = BoundaryChecker.already_processed(last_reset, boundary)

        assert result is True

    def test_returns_false_when_reset_before_boundary(self) -> None:
        """Returns False when last_dawn_reset is before boundary."""
        boundary = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        last_reset = datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)

        result = BoundaryChecker.already_processed(last_reset, boundary)

        assert result is False


class TestBoundaryCheckerLogSkip:
    """Tests for BoundaryChecker.log_skip."""

    def test_logs_debug_message(self) -> None:
        """Logs debug message with context."""
        last_reset = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        boundary = datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)

        with patch("common.dawn_reset_service_helpers.field_reset_evaluator_helpers.boundary_checker.logger") as mock_logger:
            BoundaryChecker.log_skip(last_reset, boundary, "test_context")

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0]
        assert "test_context" in call_args[1]

    def test_handles_none_values_in_log(self) -> None:
        """Handles None values in log message."""
        with patch("common.dawn_reset_service_helpers.field_reset_evaluator_helpers.boundary_checker.logger") as mock_logger:
            BoundaryChecker.log_skip(None, None, "test_context")

        mock_logger.debug.assert_called_once()
