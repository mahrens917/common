"""Error analysis components: data classes, categorization, severity, and root cause."""

import socket
import urllib.error
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""

    NETWORK = "network"
    AUTHENTICATION = "authentication"
    DATA = "data"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    RESOURCE = "resource"
    WEBSOCKET = "websocket"
    API = "api"
    UNKNOWN = "unknown"


@dataclass
class ErrorAnalysis:
    """Comprehensive error analysis result"""

    service_name: str
    error_message: str
    error_type: str
    category: ErrorCategory
    severity: ErrorSeverity
    root_cause: str
    suggested_action: str
    timestamp: float
    stack_trace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    recovery_possible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result["category"] = self.category.value
        result["severity"] = self.severity.value
        result["timestamp_iso"] = datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat()
        return result


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


_CATEGORY_CHECKERS = [
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

    def categorize_error(self, error: Exception, message: str, context: Optional[Dict[str, Any]]) -> ErrorCategory:
        error_type = type(error).__name__
        message_lower = message.lower()
        for category, checker in _CATEGORY_CHECKERS:
            if checker(error, error_type, message_lower, context):
                return category
        return ErrorCategory.UNKNOWN


class SeverityEvaluator:
    """Evaluates error severity based on category and context."""

    def determine_severity(self, error: Exception, category: ErrorCategory, context: Optional[Dict[str, Any]]) -> ErrorSeverity:
        """Determine error severity."""
        if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.CONFIGURATION]:
            return ErrorSeverity.CRITICAL
        if category in [ErrorCategory.DEPENDENCY, ErrorCategory.WEBSOCKET]:
            return ErrorSeverity.HIGH
        if category in [ErrorCategory.NETWORK, ErrorCategory.API]:
            return ErrorSeverity.MEDIUM
        return ErrorSeverity.LOW


_CONST_1006 = 1006


class RootCauseIdentifier:
    """Identifies root causes of errors based on category and message patterns."""

    def identify_root_cause(
        self,
        error: Exception,
        message: str,
        category: ErrorCategory,
        context: Optional[Dict[str, Any]],
    ) -> str:
        """Identify the root cause of the error."""
        message_lower = message.lower()
        category_handlers = {
            ErrorCategory.NETWORK: self._identify_network_cause,
            ErrorCategory.WEBSOCKET: self._identify_websocket_cause,
            ErrorCategory.AUTHENTICATION: self._identify_auth_cause,
            ErrorCategory.API: self._identify_api_cause,
            ErrorCategory.DATA: self._identify_data_cause,
            ErrorCategory.DEPENDENCY: self._identify_dependency_cause,
            ErrorCategory.CONFIGURATION: self._identify_config_cause,
            ErrorCategory.RESOURCE: self._identify_resource_cause,
        }
        handler = category_handlers.get(category)
        if handler:
            return handler(message_lower, context)
        return f"Unknown error: {message}"

    def _identify_network_cause(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        if "timeout" in message:
            return "Network timeout - server not responding or network congestion"
        if "connection refused" in message:
            return "Connection refused - target service is down or unreachable"
        if "dns" in message or "name resolution" in message:
            return "DNS resolution failure - hostname cannot be resolved"
        return "Network connectivity issue - check network connection and firewall"

    def _identify_websocket_cause(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        if "code 1006" in message or (context and context.get("close_code") == _CONST_1006):
            return "WebSocket code 1006 abnormal closure - server terminated connection unexpectedly"
        if "code 1000" in message:
            return "WebSocket code 1000 normal closure - connection closed gracefully"
        if "code 1001" in message:
            return "WebSocket code 1001 going away - server is shutting down or restarting"
        return "WebSocket connection issue - check server status and network"

    def _identify_auth_cause(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        if "401" in message or "unauthorized" in message:
            return "Authentication failed - invalid credentials or expired token"
        if "403" in message or "forbidden" in message:
            return "Authorization failed - insufficient permissions"
        return "Authentication/authorization issue - check credentials and permissions"

    def _identify_api_cause(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        if "404" in message:
            return "API endpoint not found - check URL and API version"
        if "500" in message:
            return "Server internal error - remote service is experiencing issues"
        if "429" in message:
            return "Rate limit exceeded - too many requests to API"
        return "API communication issue - check endpoint and request format"

    def _identify_data_cause(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        if "json" in message:
            return "JSON parsing error - invalid or malformed JSON data"
        if "format" in message:
            return "Data format error - unexpected data structure or type"
        return "Data processing error - check data integrity and format"

    def _identify_dependency_cause(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        if "redis" in message:
            return "Redis connection issue - check Redis server status"
        if "database" in message:
            return "Database connection issue - check database server status"
        return "Service dependency unavailable - check upstream service status"

    def _identify_config_cause(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        return "Configuration error - check environment variables and settings"

    def _identify_resource_cause(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        return "Resource constraint - check system resources (CPU, memory, disk)"


class ActionSuggester:
    """Suggests corrective actions for different error categories."""

    def suggest_action(self, error: Exception, category: ErrorCategory, root_cause: str) -> str:
        """Suggest corrective action."""
        category_actions = {
            ErrorCategory.NETWORK: "Check network connectivity, firewall rules, and target service status",
            ErrorCategory.WEBSOCKET: self._suggest_websocket_action(root_cause),
            ErrorCategory.AUTHENTICATION: "Verify credentials, check token expiration, and refresh authentication",
            ErrorCategory.API: "Check API documentation, verify endpoint URL, and implement retry logic",
            ErrorCategory.DATA: "Validate data source, check data format, and implement error handling",
            ErrorCategory.DEPENDENCY: "Check dependency service status and implement dependency monitoring",
            ErrorCategory.CONFIGURATION: "Review configuration files and environment variables",
            ErrorCategory.RESOURCE: "Monitor system resources and consider scaling or optimization",
            ErrorCategory.UNKNOWN: "Review error details and implement appropriate error handling",
        }
        return category_actions[category]

    def _suggest_websocket_action(self, root_cause: str) -> str:
        if "code 1006" in root_cause.lower():
            return "Implement immediate reconnection with exponential backoff"
        return "Check WebSocket server status and implement reconnection logic"
