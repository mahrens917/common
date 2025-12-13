"""Signature adaptation for different checker types."""

from typing import Callable


class SignatureAdapter:
    """Adapts checker method calls based on their signature requirements."""

    _MISSING_SIGNATURE = object()

    # Maps checker names to their required argument types
    _CHECKER_SIGNATURES = {
        "_is_api_error": "error_message",
        "_is_network_error": "error_type_message",
        "_is_websocket_error": "type_message",
        "_is_data_error": "type_message",
        "_is_dependency_error": "message",
        "_is_authentication_error": "message",
        "_is_configuration_error": "message",
        "_is_resource_error": "message",
    }

    @classmethod
    def call_checker(
        cls,
        checker: Callable,
        checker_name: str,
        error: Exception,
        error_type: str,
        message_lower: str,
    ) -> bool:
        """Call checker with appropriate arguments based on signature."""
        signature_type = cls._CHECKER_SIGNATURES.get(checker_name, cls._MISSING_SIGNATURE)
        if signature_type is cls._MISSING_SIGNATURE:
            signature_type = "message"

        if signature_type == "error_message":
            return checker(error, message_lower)
        if signature_type == "error_type_message":
            return checker(error, error_type, message_lower)
        if signature_type == "type_message":
            return checker(error_type, message_lower)
        return checker(message_lower)
