"""Tests for kalshi_api client_helpers errors."""

from common.kalshi_api.client_helpers.errors import KalshiClientError, KalshiErrorBase


def test_kalshi_error_base_message():
    err = KalshiErrorBase("test message")
    assert str(err) == "test message"


def test_kalshi_error_base_kwargs():
    err = KalshiErrorBase("test", foo="bar", count=42)
    assert err.foo == "bar"
    assert err.count == 42


def test_kalshi_client_error_inherits_from_base():
    err = KalshiClientError("client error")
    assert isinstance(err, KalshiErrorBase)
    assert isinstance(err, RuntimeError)
    assert str(err) == "client error"


def test_kalshi_client_error_with_kwargs():
    err = KalshiClientError("failed", status=500, path="/api/test")
    assert err.status == 500
    assert err.path == "/api/test"
