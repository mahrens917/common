"""Tests for signature adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.common.error_analyzer_helpers.error_categorizer_helpers.signature_adapter import (
    SignatureAdapter,
)


class TestSignatureAdapter:
    """Tests for SignatureAdapter class."""

    def test_checker_signatures_is_dict(self) -> None:
        """_CHECKER_SIGNATURES is a dict."""
        assert isinstance(SignatureAdapter._CHECKER_SIGNATURES, dict)

    def test_checker_signatures_has_api_error(self) -> None:
        """_CHECKER_SIGNATURES has _is_api_error."""
        assert "_is_api_error" in SignatureAdapter._CHECKER_SIGNATURES
        assert SignatureAdapter._CHECKER_SIGNATURES["_is_api_error"] == "error_message"

    def test_checker_signatures_has_network_error(self) -> None:
        """_CHECKER_SIGNATURES has _is_network_error."""
        assert "_is_network_error" in SignatureAdapter._CHECKER_SIGNATURES
        assert SignatureAdapter._CHECKER_SIGNATURES["_is_network_error"] == "error_type_message"

    def test_checker_signatures_has_websocket_error(self) -> None:
        """_CHECKER_SIGNATURES has _is_websocket_error."""
        assert "_is_websocket_error" in SignatureAdapter._CHECKER_SIGNATURES
        assert SignatureAdapter._CHECKER_SIGNATURES["_is_websocket_error"] == "type_message"

    def test_checker_signatures_has_data_error(self) -> None:
        """_CHECKER_SIGNATURES has _is_data_error."""
        assert "_is_data_error" in SignatureAdapter._CHECKER_SIGNATURES
        assert SignatureAdapter._CHECKER_SIGNATURES["_is_data_error"] == "type_message"

    def test_checker_signatures_has_dependency_error(self) -> None:
        """_CHECKER_SIGNATURES has _is_dependency_error."""
        assert "_is_dependency_error" in SignatureAdapter._CHECKER_SIGNATURES
        assert SignatureAdapter._CHECKER_SIGNATURES["_is_dependency_error"] == "message"

    def test_checker_signatures_has_authentication_error(self) -> None:
        """_CHECKER_SIGNATURES has _is_authentication_error."""
        assert "_is_authentication_error" in SignatureAdapter._CHECKER_SIGNATURES
        assert SignatureAdapter._CHECKER_SIGNATURES["_is_authentication_error"] == "message"

    def test_checker_signatures_has_configuration_error(self) -> None:
        """_CHECKER_SIGNATURES has _is_configuration_error."""
        assert "_is_configuration_error" in SignatureAdapter._CHECKER_SIGNATURES
        assert SignatureAdapter._CHECKER_SIGNATURES["_is_configuration_error"] == "message"

    def test_checker_signatures_has_resource_error(self) -> None:
        """_CHECKER_SIGNATURES has _is_resource_error."""
        assert "_is_resource_error" in SignatureAdapter._CHECKER_SIGNATURES
        assert SignatureAdapter._CHECKER_SIGNATURES["_is_resource_error"] == "message"


class TestCallChecker:
    """Tests for call_checker method."""

    def test_calls_api_error_with_error_and_message(self) -> None:
        """Calls _is_api_error with error and message_lower."""
        checker = MagicMock(return_value=True)
        error = ValueError("api error")

        result = SignatureAdapter.call_checker(
            checker=checker,
            checker_name="_is_api_error",
            error=error,
            error_type="ValueError",
            message_lower="api error",
        )

        checker.assert_called_once_with(error, "api error")
        assert result is True

    def test_calls_network_error_with_error_type_message(self) -> None:
        """Calls _is_network_error with error, error_type, and message_lower."""
        checker = MagicMock(return_value=True)
        error = ConnectionError("network error")

        result = SignatureAdapter.call_checker(
            checker=checker,
            checker_name="_is_network_error",
            error=error,
            error_type="ConnectionError",
            message_lower="network error",
        )

        checker.assert_called_once_with(error, "ConnectionError", "network error")
        assert result is True

    def test_calls_websocket_error_with_type_message(self) -> None:
        """Calls _is_websocket_error with error_type and message_lower."""
        checker = MagicMock(return_value=True)
        error = RuntimeError("websocket error")

        result = SignatureAdapter.call_checker(
            checker=checker,
            checker_name="_is_websocket_error",
            error=error,
            error_type="RuntimeError",
            message_lower="websocket error",
        )

        checker.assert_called_once_with("RuntimeError", "websocket error")
        assert result is True

    def test_calls_data_error_with_type_message(self) -> None:
        """Calls _is_data_error with error_type and message_lower."""
        checker = MagicMock(return_value=False)
        error = ValueError("data error")

        result = SignatureAdapter.call_checker(
            checker=checker,
            checker_name="_is_data_error",
            error=error,
            error_type="ValueError",
            message_lower="data error",
        )

        checker.assert_called_once_with("ValueError", "data error")
        assert result is False

    def test_calls_dependency_error_with_message_only(self) -> None:
        """Calls _is_dependency_error with only message_lower."""
        checker = MagicMock(return_value=True)
        error = RuntimeError("dependency error")

        result = SignatureAdapter.call_checker(
            checker=checker,
            checker_name="_is_dependency_error",
            error=error,
            error_type="RuntimeError",
            message_lower="dependency error",
        )

        checker.assert_called_once_with("dependency error")
        assert result is True

    def test_calls_authentication_error_with_message_only(self) -> None:
        """Calls _is_authentication_error with only message_lower."""
        checker = MagicMock(return_value=True)
        error = PermissionError("auth error")

        result = SignatureAdapter.call_checker(
            checker=checker,
            checker_name="_is_authentication_error",
            error=error,
            error_type="PermissionError",
            message_lower="auth error",
        )

        checker.assert_called_once_with("auth error")
        assert result is True

    def test_calls_configuration_error_with_message_only(self) -> None:
        """Calls _is_configuration_error with only message_lower."""
        checker = MagicMock(return_value=False)
        error = FileNotFoundError("config error")

        result = SignatureAdapter.call_checker(
            checker=checker,
            checker_name="_is_configuration_error",
            error=error,
            error_type="FileNotFoundError",
            message_lower="config error",
        )

        checker.assert_called_once_with("config error")
        assert result is False

    def test_calls_resource_error_with_message_only(self) -> None:
        """Calls _is_resource_error with only message_lower."""
        checker = MagicMock(return_value=True)
        error = MemoryError("resource error")

        result = SignatureAdapter.call_checker(
            checker=checker,
            checker_name="_is_resource_error",
            error=error,
            error_type="MemoryError",
            message_lower="resource error",
        )

        checker.assert_called_once_with("resource error")
        assert result is True

    def test_calls_unknown_checker_with_message_only(self) -> None:
        """Calls unknown checker with only message_lower (default behavior)."""
        checker = MagicMock(return_value=True)
        error = RuntimeError("unknown error")

        result = SignatureAdapter.call_checker(
            checker=checker,
            checker_name="_is_unknown_error",
            error=error,
            error_type="RuntimeError",
            message_lower="unknown error",
        )

        checker.assert_called_once_with("unknown error")
        assert result is True

    def test_returns_checker_result(self) -> None:
        """Returns the result from the checker."""
        checker_true = MagicMock(return_value=True)
        checker_false = MagicMock(return_value=False)
        error = RuntimeError("test")

        result_true = SignatureAdapter.call_checker(
            checker=checker_true,
            checker_name="_is_resource_error",
            error=error,
            error_type="RuntimeError",
            message_lower="test",
        )

        result_false = SignatureAdapter.call_checker(
            checker=checker_false,
            checker_name="_is_resource_error",
            error=error,
            error_type="RuntimeError",
            message_lower="test",
        )

        assert result_true is True
        assert result_false is False
