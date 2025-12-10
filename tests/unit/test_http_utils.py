from types import SimpleNamespace

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
