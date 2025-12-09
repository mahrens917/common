"""Action suggestion for error recovery."""

import logging

from .data_classes import ErrorCategory

logger = logging.getLogger(__name__)


class ActionSuggester:
    """Suggests corrective actions for different error categories."""

    def suggest_action(self, error: Exception, category: ErrorCategory, root_cause: str) -> str:
        """Suggest corrective action."""
        category_actions = {
            ErrorCategory.NETWORK: self._suggest_network_action,
            ErrorCategory.WEBSOCKET: self._suggest_websocket_action,
            ErrorCategory.AUTHENTICATION: self._suggest_auth_action,
            ErrorCategory.API: self._suggest_api_action,
            ErrorCategory.DATA: self._suggest_data_action,
            ErrorCategory.DEPENDENCY: self._suggest_dependency_action,
            ErrorCategory.CONFIGURATION: self._suggest_config_action,
            ErrorCategory.RESOURCE: self._suggest_resource_action,
        }

        handler = category_actions.get(category)
        if handler:
            return handler(root_cause)

        return "Review error details and implement appropriate error handling"

    def _suggest_network_action(self, root_cause: str) -> str:
        """Suggest action for network errors."""
        return "Check network connectivity, firewall rules, and target service status"

    def _suggest_websocket_action(self, root_cause: str) -> str:
        """Suggest action for WebSocket errors."""
        if "code 1006" in root_cause.lower():
            return "Implement immediate reconnection with exponential backoff"
        return "Check WebSocket server status and implement reconnection logic"

    def _suggest_auth_action(self, root_cause: str) -> str:
        """Suggest action for authentication errors."""
        return "Verify credentials, check token expiration, and refresh authentication"

    def _suggest_api_action(self, root_cause: str) -> str:
        """Suggest action for API errors."""
        return "Check API documentation, verify endpoint URL, and implement retry logic"

    def _suggest_data_action(self, root_cause: str) -> str:
        """Suggest action for data errors."""
        return "Validate data source, check data format, and implement error handling"

    def _suggest_dependency_action(self, root_cause: str) -> str:
        """Suggest action for dependency errors."""
        return "Check dependency service status and implement dependency monitoring"

    def _suggest_config_action(self, root_cause: str) -> str:
        """Suggest action for configuration errors."""
        return "Review configuration files and environment variables"

    def _suggest_resource_action(self, root_cause: str) -> str:
        """Suggest action for resource errors."""
        return "Monitor system resources and consider scaling or optimization"
