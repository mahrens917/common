"""Tests for error builder module."""

from unittest.mock import patch

import pytest

from common.connection_state_tracker_helpers.error_builder import (
    ConnectionStateTrackerError,
    build_tracker_error,
)


class TestConnectionStateTrackerError:
    """Tests for ConnectionStateTrackerError exception class."""

    def test_is_runtime_error(self) -> None:
        """Is a subclass of RuntimeError."""
        error = ConnectionStateTrackerError("test message")

        assert isinstance(error, RuntimeError)

    def test_has_message(self) -> None:
        """Has the provided message."""
        error = ConnectionStateTrackerError("test message")

        assert str(error) == "test message"


class TestBuildTrackerError:
    """Tests for build_tracker_error function."""

    def test_returns_connection_state_tracker_error(self) -> None:
        """Returns ConnectionStateTrackerError instance."""
        original = ValueError("original error")

        with patch("common.connection_state_tracker_helpers.error_builder.logger"):
            result = build_tracker_error("Failed to persist", original)

        assert isinstance(result, ConnectionStateTrackerError)

    def test_error_has_message(self) -> None:
        """Returned error has the provided message."""
        original = ValueError("original error")

        with patch("common.connection_state_tracker_helpers.error_builder.logger"):
            result = build_tracker_error("Failed to persist", original)

        assert str(result) == "Failed to persist"

    def test_error_has_cause(self) -> None:
        """Returned error has original error as cause."""
        original = ValueError("original error")

        with patch("common.connection_state_tracker_helpers.error_builder.logger"):
            result = build_tracker_error("Failed to persist", original)

        assert result.__cause__ is original

    def test_logs_exception(self) -> None:
        """Logs the exception with context."""
        original = ValueError("original error")

        with patch(
            "common.connection_state_tracker_helpers.error_builder.logger"
        ) as mock_logger:
            build_tracker_error("Failed to persist", original)

            mock_logger.exception.assert_called_once()
            call_args = mock_logger.exception.call_args
            assert call_args[0][1] == "Failed to persist"
