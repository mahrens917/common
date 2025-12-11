from types import SimpleNamespace

import pytest

from common import http_utils


def test_is_aiohttp_session_open_returns_false_for_none() -> None:
    assert not http_utils.is_aiohttp_session_open(None)


def test_is_aiohttp_session_open_returns_false_when_closed_attribute_true() -> None:
    session = SimpleNamespace(closed=True)
    assert not http_utils.is_aiohttp_session_open(session)


def test_is_aiohttp_session_open_returns_false_when_closed_attribute_missing() -> None:
    session = SimpleNamespace()
    assert not http_utils.is_aiohttp_session_open(session)


def test_is_aiohttp_session_open_returns_true_when_closed_attribute_false() -> None:
    session = SimpleNamespace(closed=False)
    assert http_utils.is_aiohttp_session_open(session)


def test_aiohttp_session_connection_mixin_uses_session_state() -> None:
    class Dummy(http_utils.AioHTTPSessionConnectionMixin):
        def __init__(self, closed: bool):
            self.session = SimpleNamespace(closed=closed)

    assert Dummy(closed=False).is_connected()
    assert not Dummy(closed=True).is_connected()


def test_aiohttp_session_connection_mixin_no_session_attribute() -> None:
    class DummyNoSession(http_utils.AioHTTPSessionConnectionMixin):
        pass

    instance = DummyNoSession()
    assert not instance.is_connected()


def test_aiohttp_session_connection_mixin_none_session() -> None:
    class DummyNoneSession(http_utils.AioHTTPSessionConnectionMixin):
        def __init__(self):
            self.session = None

    instance = DummyNoneSession()
    assert not instance.is_connected()


def test_ensure_http_url_valid_http() -> None:
    url = "http://example.com/path"
    assert http_utils.ensure_http_url(url) == url


def test_ensure_http_url_valid_https() -> None:
    url = "https://example.com/path"
    assert http_utils.ensure_http_url(url) == url


def test_ensure_http_url_invalid_scheme() -> None:
    with pytest.raises(ValueError, match="Unsupported URL scheme"):
        http_utils.ensure_http_url("ftp://example.com")


def test_ensure_http_url_missing_netloc() -> None:
    with pytest.raises(ValueError, match="URL missing network location"):
        http_utils.ensure_http_url("http://")


def test_ensure_http_url_uppercase_scheme() -> None:
    url = "HTTP://example.com"
    assert http_utils.ensure_http_url(url) == url


def test_ensure_http_url_with_port() -> None:
    url = "https://example.com:8080/path"
    assert http_utils.ensure_http_url(url) == url


def test_ensure_http_url_with_query() -> None:
    url = "https://example.com/path?key=value"
    assert http_utils.ensure_http_url(url) == url
