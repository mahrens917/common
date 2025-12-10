"""Tests for error_classifier module."""

from __future__ import annotations

import pytest

from common.reconnection_error_patterns_helpers.error_classifier import (
    ErrorTypeClassifier,
)


class TestErrorTypeClassifierClassify:
    """Tests for ErrorTypeClassifier.classify method."""

    def test_returns_unknown_for_empty_message(self) -> None:
        """Returns 'unknown' for empty error message."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("")

        assert result == "unknown"

    def test_returns_unknown_for_none_like_empty(self) -> None:
        """Returns 'unknown' for falsy empty string."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("")

        assert result == "unknown"

    def test_returns_general_error_for_unrecognized_message(self) -> None:
        """Returns 'general_error' for unrecognized messages."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("Some random error message")

        assert result == "general_error"


class TestConnectionErrorClassification:
    """Tests for connection error classification."""

    def test_classifies_connection_timeout(self) -> None:
        """Classifies connection timeout errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("Connection timeout after 30 seconds")

        assert result == "connection_timeout"

    def test_classifies_connection_timed_out(self) -> None:
        """Classifies connection timed out errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("Connection timed out")

        assert result == "connection_timeout"

    def test_classifies_connection_reset(self) -> None:
        """Classifies connection reset errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("Connection reset by peer")

        assert result == "connection_lost"

    def test_classifies_connection_closed(self) -> None:
        """Classifies connection closed errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("Connection was closed unexpectedly")

        assert result == "connection_lost"

    def test_classifies_connection_lost(self) -> None:
        """Classifies connection lost errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("Connection lost during operation")

        assert result == "connection_lost"

    def test_classifies_connection_refused(self) -> None:
        """Classifies connection refused errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("Connection refused by host")

        assert result == "connection_failed"

    def test_classifies_connection_failed(self) -> None:
        """Classifies connection failed errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("Connection failed to establish")

        assert result == "connection_failed"

    def test_classifies_generic_connection_error(self) -> None:
        """Classifies generic connection errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("Connection error occurred")

        assert result == "connection_error"

    def test_classifies_connect_error(self) -> None:
        """Classifies connect errors (without 'ion' suffix)."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("Cannot connect to server")

        assert result == "connection_error"


class TestWebSocketErrorClassification:
    """Tests for WebSocket error classification."""

    def test_classifies_websocket_close_frame_error(self) -> None:
        """Classifies WebSocket close frame errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("WebSocket: No close frame received")

        assert result == "websocket_close_frame"

    def test_classifies_websocket_ping_error(self) -> None:
        """Classifies WebSocket ping errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("WebSocket ping timeout")

        assert result == "websocket_heartbeat"

    def test_classifies_websocket_pong_error(self) -> None:
        """Classifies WebSocket pong errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("WebSocket pong not received")

        assert result == "websocket_heartbeat"

    def test_classifies_websocket_heartbeat_error(self) -> None:
        """Classifies WebSocket heartbeat errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("WebSocket heartbeat failed")

        assert result == "websocket_heartbeat"

    def test_classifies_generic_websocket_error(self) -> None:
        """Classifies generic WebSocket errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("WebSocket error: 1006")

        assert result == "websocket_error"

    def test_classifies_ws_abbreviation_error(self) -> None:
        """Classifies ws abbreviation errors."""
        classifier = ErrorTypeClassifier()

        # Note: "ws" alone triggers websocket, but "ws connection" has "connection" first
        # which causes connection_error to take precedence. Using different wording.
        result = classifier.classify("ws protocol error")

        assert result == "websocket_error"


class TestNetworkErrorClassification:
    """Tests for network error classification."""

    def test_classifies_network_error(self) -> None:
        """Classifies network errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("Network error during request")

        assert result == "network_error"

    def test_classifies_dns_error(self) -> None:
        """Classifies DNS errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("DNS resolution failed")

        assert result == "network_error"

    def test_classifies_ssl_error(self) -> None:
        """Classifies SSL errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("SSL handshake failed")

        assert result == "network_error"

    def test_classifies_certificate_error(self) -> None:
        """Classifies certificate errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("Certificate verification failed")

        assert result == "network_error"


class TestServiceLimitErrorClassification:
    """Tests for service limit error classification."""

    def test_classifies_rate_limit_error(self) -> None:
        """Classifies rate limit errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("Rate limit exceeded")

        assert result == "service_limit"

    def test_classifies_too_many_requests_error(self) -> None:
        """Classifies too many requests errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("Too many requests: 429")

        assert result == "service_limit"

    def test_classifies_service_unavailable_error(self) -> None:
        """Classifies service unavailable errors."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("Service unavailable: 503")

        assert result == "service_limit"


class TestCaseInsensitivity:
    """Tests for case insensitive matching."""

    def test_handles_uppercase_connection_error(self) -> None:
        """Handles uppercase CONNECTION error."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("CONNECTION TIMEOUT")

        assert result == "connection_timeout"

    def test_handles_mixed_case_websocket_error(self) -> None:
        """Handles mixed case WebSocket error."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("WebSocket Error")

        assert result == "websocket_error"

    def test_handles_uppercase_rate_limit(self) -> None:
        """Handles uppercase RATE LIMIT."""
        classifier = ErrorTypeClassifier()

        result = classifier.classify("RATE LIMIT EXCEEDED")

        assert result == "service_limit"


class TestPrivateMethods:
    """Tests for private helper methods."""

    def test_is_connection_error_true(self) -> None:
        """_is_connection_error returns True for connection errors."""
        classifier = ErrorTypeClassifier()

        assert classifier._is_connection_error("connection lost") is True
        assert classifier._is_connection_error("cannot connect") is True

    def test_is_connection_error_false(self) -> None:
        """_is_connection_error returns False for non-connection errors."""
        classifier = ErrorTypeClassifier()

        assert classifier._is_connection_error("websocket error") is False
        assert classifier._is_connection_error("rate limit") is False

    def test_is_websocket_error_true(self) -> None:
        """_is_websocket_error returns True for WebSocket errors."""
        classifier = ErrorTypeClassifier()

        assert classifier._is_websocket_error("websocket failed") is True
        assert classifier._is_websocket_error("ws error") is True

    def test_is_websocket_error_false(self) -> None:
        """_is_websocket_error returns False for non-WebSocket errors."""
        classifier = ErrorTypeClassifier()

        assert classifier._is_websocket_error("connection error") is False

    def test_is_network_error_true(self) -> None:
        """_is_network_error returns True for network errors."""
        classifier = ErrorTypeClassifier()

        assert classifier._is_network_error("network failed") is True
        assert classifier._is_network_error("dns error") is True
        assert classifier._is_network_error("ssl error") is True
        assert classifier._is_network_error("certificate error") is True

    def test_is_network_error_false(self) -> None:
        """_is_network_error returns False for non-network errors."""
        classifier = ErrorTypeClassifier()

        assert classifier._is_network_error("websocket error") is False

    def test_is_service_limit_error_true(self) -> None:
        """_is_service_limit_error returns True for service limit errors."""
        classifier = ErrorTypeClassifier()

        assert classifier._is_service_limit_error("rate limit") is True
        assert classifier._is_service_limit_error("too many requests") is True
        assert classifier._is_service_limit_error("service unavailable") is True

    def test_is_service_limit_error_false(self) -> None:
        """_is_service_limit_error returns False for non-service-limit errors."""
        classifier = ErrorTypeClassifier()

        assert classifier._is_service_limit_error("connection error") is False
