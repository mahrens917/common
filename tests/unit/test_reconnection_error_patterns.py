from __future__ import annotations

import re

import pytest

from src.common.reconnection_error_patterns import (
    DEFAULT_SERVICE_TYPE_MAPPING,
    RECONNECTION_ERROR_PATTERNS,
    ReconnectionErrorClassifier,
    ServiceType,
    get_error_classifier,
)


@pytest.fixture
def classifier():
    # Work on a fresh copy to avoid global side-effects
    mapping_copy = DEFAULT_SERVICE_TYPE_MAPPING.copy()
    return ReconnectionErrorClassifier(service_type_mapping=mapping_copy)


def test_get_service_type_defaults_to_unknown(classifier):
    assert classifier.get_service_type("nonexistent") == ServiceType.UNKNOWN

    classifier.add_service_type_mapping("custom", ServiceType.REST)
    assert classifier.get_service_type("custom") == ServiceType.REST


@pytest.mark.parametrize(
    "service_name,error_message,expected",
    [
        ("deribit", "WebSocket connection lost unexpectedly", True),
        ("kalshi", "PING timeout after 30s", True),
        ("kalshi", "Unhandled error in processing", False),
        ("unknown", "connection timeout", False),
        ("tracker", "SSL handshake failed for upstream", True),
    ],
)
def test_is_reconnection_error(classifier, service_name, error_message, expected):
    assert classifier.is_reconnection_error(service_name, error_message) is expected


def test_is_reconnection_error_handles_empty_message(classifier):
    assert classifier.is_reconnection_error("deribit", "") is False


@pytest.mark.parametrize(
    "service_type,error_message,expected",
    [
        ("websocket", "pong timeout detected", True),
        ("rest", "connection refused by host", True),
        ("scraper", "rate limit exceeded", True),
        ("database", "server has gone away", True),
        ("unknown", "connection timeout", False),
    ],
)
def test_is_reconnection_error_by_type(classifier, service_type, error_message, expected):
    assert classifier.is_reconnection_error_by_type(service_type, error_message) is expected


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Connection timed out after 5s", "connection_timeout"),
        ("Connection reset by peer", "connection_lost"),
        ("Connection refused by server", "connection_failed"),
        ("Websocket close frame missing", "websocket_close_frame"),
        ("Generic websocket error", "websocket_error"),
        ("SSL certificate verify failed", "network_error"),
        ("Too many requests received", "service_limit"),
        ("Unexpected error occurred", "general_error"),
        ("", "unknown"),
    ],
)
def test_classify_error_type(classifier, message, expected):
    assert classifier.classify_error_type("kalshi", message) == expected


def test_get_reconnection_patterns_for_service_returns_patterns(classifier):
    patterns = classifier.get_reconnection_patterns_for_service("deribit")
    assert patterns == RECONNECTION_ERROR_PATTERNS[ServiceType.WEBSOCKET]


def test_add_custom_pattern_updates_compiled_patterns(classifier):
    custom_pattern = r"temporary glitch"
    classifier.add_custom_pattern(ServiceType.WEBSOCKET, custom_pattern)

    compiled = classifier.pattern_compiler.compiled_patterns[ServiceType.WEBSOCKET]
    assert any(pattern.pattern == custom_pattern for pattern in compiled)
    assert classifier.is_reconnection_error("deribit", "Temporary glitch in socket") is True


def test_global_classifier_cached_instance():
    first = get_error_classifier()
    second = get_error_classifier()
    assert first is second
