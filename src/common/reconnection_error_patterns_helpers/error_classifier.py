"""Error type classification for detailed analysis."""

import logging

logger = logging.getLogger(__name__)


class ErrorTypeClassifier:
    """Classifies errors into specific categories."""

    def classify(self, error_message: str) -> str:
        """
        Classify the type of error for detailed analysis.

        Args:
            error_message: Error message to analyze

        Returns:
            Error type classification string
        """
        if not error_message:
            return "unknown"

        error_lower = error_message.lower()

        # Connection-related errors
        if self._is_connection_error(error_lower):
            return self._classify_connection_error(error_lower)

        # WebSocket-specific errors
        if self._is_websocket_error(error_lower):
            return self._classify_websocket_error(error_lower)

        # Network-related errors
        if self._is_network_error(error_lower):
            return "network_error"

        # Rate limiting and service errors
        if self._is_service_limit_error(error_lower):
            return "service_limit"

        return "general_error"

    def _is_connection_error(self, error_lower: str) -> bool:
        """Check if error is connection-related."""
        return any(term in error_lower for term in ["connection", "connect"])

    def _classify_connection_error(self, error_lower: str) -> str:
        """Classify specific connection error type."""
        if any(term in error_lower for term in ["timeout", "timed out"]):
            return "connection_timeout"
        if any(term in error_lower for term in ["reset", "closed", "lost"]):
            return "connection_lost"
        if any(term in error_lower for term in ["refused", "failed"]):
            return "connection_failed"
        return "connection_error"

    def _is_websocket_error(self, error_lower: str) -> bool:
        """Check if error is WebSocket-related."""
        return any(term in error_lower for term in ["websocket", "ws"])

    def _classify_websocket_error(self, error_lower: str) -> str:
        """Classify specific WebSocket error type."""
        if "close frame" in error_lower:
            return "websocket_close_frame"
        if any(term in error_lower for term in ["ping", "pong", "heartbeat"]):
            return "websocket_heartbeat"
        return "websocket_error"

    def _is_network_error(self, error_lower: str) -> bool:
        """Check if error is network-related."""
        return any(term in error_lower for term in ["network", "dns", "ssl", "certificate"])

    def _is_service_limit_error(self, error_lower: str) -> bool:
        """Check if error is service limit/rate limiting related."""
        return any(term in error_lower for term in ["rate limit", "too many requests", "service unavailable"])
