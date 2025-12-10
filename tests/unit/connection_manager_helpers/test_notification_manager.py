"""Tests for the NotificationManager stub."""

import pytest

from common.connection_manager_helpers.notification_manager import NotificationManager


class TestNotificationManager:
    def test_init_stores_kwargs_and_tracks_shutdown_flag(self) -> None:
        """Constructor should capture kwargs and leave shutdown unset."""
        manager = NotificationManager(foo="bar", retries=3)

        assert manager.foo == "bar"
        assert manager.retries == 3
        assert manager._shutdown_requested is False

    def test_request_shutdown_marks_component(self) -> None:
        """The mixin should expose a toggled shutdown flag."""
        manager = NotificationManager()

        manager.request_shutdown()

        assert manager._shutdown_requested is True

    @pytest.mark.asyncio
    async def test_notify_stub_raises(self) -> None:
        """The stub raises a NotImplementedError so concrete classes must override."""
        manager = NotificationManager()

        with pytest.raises(NotImplementedError):
            await manager.notify()
