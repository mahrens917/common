"""Tests for checker dispatcher."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.common.error_analyzer_helpers.error_categorizer_helpers.checker_dispatcher import (
    dispatch_category_check,
)


class TestDispatchCategoryCheck:
    """Tests for dispatch_category_check function."""

    def test_dispatches_api_error_checker(self) -> None:
        """Dispatches _is_api_error with error and message_lower."""
        checker = MagicMock(return_value=True)
        error = ValueError("test error")

        result = dispatch_category_check(
            checker=checker,
            checker_name="_is_api_error",
            error=error,
            error_type="ValueError",
            message_lower="test error",
        )

        checker.assert_called_once_with(error, "test error")
        assert result is True

    def test_dispatches_network_error_checker(self) -> None:
        """Dispatches _is_network_error with error, error_type, and message_lower."""
        checker = MagicMock(return_value=True)
        error = ConnectionError("connection failed")

        result = dispatch_category_check(
            checker=checker,
            checker_name="_is_network_error",
            error=error,
            error_type="ConnectionError",
            message_lower="connection failed",
        )

        checker.assert_called_once_with(error, "ConnectionError", "connection failed")
        assert result is True

    def test_dispatches_websocket_error_checker(self) -> None:
        """Dispatches _is_websocket_error with error_type and message_lower."""
        checker = MagicMock(return_value=True)
        error = RuntimeError("websocket closed")

        result = dispatch_category_check(
            checker=checker,
            checker_name="_is_websocket_error",
            error=error,
            error_type="RuntimeError",
            message_lower="websocket closed",
        )

        checker.assert_called_once_with("RuntimeError", "websocket closed")
        assert result is True

    def test_dispatches_data_error_checker(self) -> None:
        """Dispatches _is_data_error with error_type and message_lower."""
        checker = MagicMock(return_value=False)
        error = ValueError("invalid data")

        result = dispatch_category_check(
            checker=checker,
            checker_name="_is_data_error",
            error=error,
            error_type="ValueError",
            message_lower="invalid data",
        )

        checker.assert_called_once_with("ValueError", "invalid data")
        assert result is False

    def test_dispatches_default_checker_with_message_only(self) -> None:
        """Dispatches other checkers with only message_lower."""
        checker = MagicMock(return_value=True)
        error = RuntimeError("some error")

        result = dispatch_category_check(
            checker=checker,
            checker_name="_is_dependency_error",
            error=error,
            error_type="RuntimeError",
            message_lower="some error",
        )

        checker.assert_called_once_with("some error")
        assert result is True

    def test_dispatches_authentication_error_with_message_only(self) -> None:
        """Dispatches _is_authentication_error with only message_lower."""
        checker = MagicMock(return_value=True)
        error = PermissionError("access denied")

        result = dispatch_category_check(
            checker=checker,
            checker_name="_is_authentication_error",
            error=error,
            error_type="PermissionError",
            message_lower="access denied",
        )

        checker.assert_called_once_with("access denied")
        assert result is True

    def test_dispatches_configuration_error_with_message_only(self) -> None:
        """Dispatches _is_configuration_error with only message_lower."""
        checker = MagicMock(return_value=False)
        error = FileNotFoundError("config not found")

        result = dispatch_category_check(
            checker=checker,
            checker_name="_is_configuration_error",
            error=error,
            error_type="FileNotFoundError",
            message_lower="config not found",
        )

        checker.assert_called_once_with("config not found")
        assert result is False

    def test_dispatches_resource_error_with_message_only(self) -> None:
        """Dispatches _is_resource_error with only message_lower."""
        checker = MagicMock(return_value=True)
        error = MemoryError("out of memory")

        result = dispatch_category_check(
            checker=checker,
            checker_name="_is_resource_error",
            error=error,
            error_type="MemoryError",
            message_lower="out of memory",
        )

        checker.assert_called_once_with("out of memory")
        assert result is True

    def test_returns_checker_result(self) -> None:
        """Returns the result from the checker."""
        checker_true = MagicMock(return_value=True)
        checker_false = MagicMock(return_value=False)
        error = RuntimeError("test")

        result_true = dispatch_category_check(
            checker=checker_true,
            checker_name="_is_resource_error",
            error=error,
            error_type="RuntimeError",
            message_lower="test",
        )

        result_false = dispatch_category_check(
            checker=checker_false,
            checker_name="_is_resource_error",
            error=error,
            error_type="RuntimeError",
            message_lower="test",
        )

        assert result_true is True
        assert result_false is False
