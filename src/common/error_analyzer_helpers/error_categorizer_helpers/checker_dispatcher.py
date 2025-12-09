"""Dispatcher for error category checkers."""

from typing import Callable


def dispatch_category_check(
    checker: Callable, checker_name: str, error: Exception, error_type: str, message_lower: str
) -> bool:
    """
    Dispatch to the appropriate checker based on its signature.

    Returns:
        True if the error matches the category, False otherwise
    """
    if checker_name == "_is_api_error":
        return checker(error, message_lower)
    elif checker_name == "_is_network_error":
        return checker(error, error_type, message_lower)
    elif checker_name in ("_is_websocket_error", "_is_data_error"):
        return checker(error_type, message_lower)
    else:
        return checker(message_lower)
