"""Root cause identification for errors."""

import logging
from typing import Any, Dict, Optional

from .data_classes import ErrorCategory

logger = logging.getLogger(__name__)


# Constants
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
        """Identify network-related error causes."""
        if "timeout" in message:
            return "Network timeout - server not responding or network congestion"
        if "connection refused" in message:
            return "Connection refused - target service is down or unreachable"
        if "dns" in message or "name resolution" in message:
            return "DNS resolution failure - hostname cannot be resolved"
        return "Network connectivity issue - check network connection and firewall"

    def _identify_websocket_cause(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        """Identify WebSocket-related error causes."""
        if "code 1006" in message or (context and context.get("close_code") == _CONST_1006):
            return "WebSocket code 1006 abnormal closure - server terminated connection unexpectedly"
        if "code 1000" in message:
            return "WebSocket code 1000 normal closure - connection closed gracefully"
        if "code 1001" in message:
            return "WebSocket code 1001 going away - server is shutting down or restarting"
        return "WebSocket connection issue - check server status and network"

    def _identify_auth_cause(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        """Identify authentication/authorization error causes."""
        if "401" in message or "unauthorized" in message:
            return "Authentication failed - invalid credentials or expired token"
        if "403" in message or "forbidden" in message:
            return "Authorization failed - insufficient permissions"
        return "Authentication/authorization issue - check credentials and permissions"

    def _identify_api_cause(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        """Identify API-related error causes."""
        if "404" in message:
            return "API endpoint not found - check URL and API version"
        if "500" in message:
            return "Server internal error - remote service is experiencing issues"
        if "429" in message:
            return "Rate limit exceeded - too many requests to API"
        return "API communication issue - check endpoint and request format"

    def _identify_data_cause(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        """Identify data processing error causes."""
        if "json" in message:
            return "JSON parsing error - invalid or malformed JSON data"
        if "format" in message:
            return "Data format error - unexpected data structure or type"
        return "Data processing error - check data integrity and format"

    def _identify_dependency_cause(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        """Identify service dependency error causes."""
        if "redis" in message:
            return "Redis connection issue - check Redis server status"
        if "database" in message:
            return "Database connection issue - check database server status"
        return "Service dependency unavailable - check upstream service status"

    def _identify_config_cause(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        """Identify configuration error causes."""
        return "Configuration error - check environment variables and settings"

    def _identify_resource_cause(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        """Identify resource constraint error causes."""
        return "Resource constraint - check system resources (CPU, memory, disk)"
