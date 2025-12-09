"""Error categorization for error analyzer."""

import logging
import socket
import urllib.error
from typing import Any, Dict, Optional

from .data_classes import ErrorCategory

logger = logging.getLogger(__name__)


def _check_websocket(_: Exception, error_type: str, message_lower: str, __) -> bool:
    lowered_type = error_type.lower()
    if "websocket" in lowered_type or "websocket" in message_lower:
        return True
    if "connectionclosed" in lowered_type:
        return True
    websocket_keywords = ["code 1006", "abnormal closure", "close frame"]
    return any(keyword in message_lower for keyword in websocket_keywords)


def _check_api(error: Exception, __: str, message_lower: str, ___) -> bool:
    if isinstance(error, (urllib.error.URLError, urllib.error.HTTPError)):
        return True
    api_keywords = ["api", "http", "status code", "response"]
    return any(keyword in message_lower for keyword in api_keywords)


def _check_dependency(_: Exception, __: str, message_lower: str, ___) -> bool:
    dependency_keywords = [
        "redis connection",
        "database connection",
        "dependency",
        "service unavailable",
        "market data not available",
    ]
    if any(keyword in message_lower for keyword in dependency_keywords):
        return True
    has_key = "key" in message_lower
    has_not_found = "not found" in message_lower
    has_market_context = "market" in message_lower or "deribit" in message_lower
    return has_key and has_not_found and has_market_context


def _check_network(error: Exception, error_type: str, message_lower: str, ___) -> bool:
    if isinstance(error, (ConnectionError, TimeoutError, socket.error)):
        return True
    network_type_keywords = ["connection", "timeout", "network"]
    if any(keyword in error_type.lower() for keyword in network_type_keywords):
        return True
    network_msg_keywords = ["connection", "timeout", "network", "unreachable"]
    return any(keyword in message_lower for keyword in network_msg_keywords)


def _check_auth(_: Exception, __: str, message_lower: str, ___) -> bool:
    auth_keywords = ["auth", "401", "unauthorized", "forbidden", "403"]
    return any(keyword in message_lower for keyword in auth_keywords)


def _check_data(_: Exception, error_type: str, message_lower: str, ___) -> bool:
    data_type_keywords = ["json", "parse", "decode", "format"]
    if any(keyword in error_type.lower() for keyword in data_type_keywords):
        return True
    data_msg_keywords = ["json", "parse", "decode", "format", "invalid data"]
    return any(keyword in message_lower for keyword in data_msg_keywords)


def _check_config(_: Exception, __: str, message_lower: str, ___) -> bool:
    config_keywords = ["config", "environment", "missing", "not found"]
    return any(keyword in message_lower for keyword in config_keywords)


def _check_resource(_: Exception, __: str, message_lower: str, ___) -> bool:
    resource_keywords = ["memory", "disk", "cpu", "resource"]
    return any(keyword in message_lower for keyword in resource_keywords)


CATEGORY_CHECKERS = [
    (ErrorCategory.WEBSOCKET, _check_websocket),
    (ErrorCategory.API, _check_api),
    (ErrorCategory.DEPENDENCY, _check_dependency),
    (ErrorCategory.NETWORK, _check_network),
    (ErrorCategory.AUTHENTICATION, _check_auth),
    (ErrorCategory.DATA, _check_data),
    (ErrorCategory.CONFIGURATION, _check_config),
    (ErrorCategory.RESOURCE, _check_resource),
]


class ErrorCategorizer:
    """Categorizes errors into defined categories based on type and message patterns."""

    def categorize_error(
        self, error: Exception, message: str, context: Optional[Dict[str, Any]]
    ) -> ErrorCategory:
        error_type = type(error).__name__
        message_lower = message.lower()
        for category, checker in CATEGORY_CHECKERS:
            if checker(error, error_type, message_lower, context):
                return category
        return ErrorCategory.UNKNOWN
