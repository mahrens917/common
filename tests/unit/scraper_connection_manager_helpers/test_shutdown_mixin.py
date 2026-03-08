"""Tests for shutdown_mixin module."""

from common.scraper_connection_manager_helpers.shutdown_mixin import ShutdownRequestMixin


class _Concrete(ShutdownRequestMixin):
    def __init__(self) -> None:
        self._shutdown_requested = False


class TestShutdownRequestMixin:
    def test_request_shutdown_sets_flag(self) -> None:
        obj = _Concrete()
        assert obj._shutdown_requested is False
        obj.request_shutdown()
        assert obj._shutdown_requested is True
