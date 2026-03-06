"""Stub manager classes for connection_manager components."""

import logging

from .shutdown_mixin import ShutdownRequestMixin

logger = logging.getLogger(__name__)


class StateManager(ShutdownRequestMixin):
    """Handles transition_state operations."""

    def __init__(self, *args, **kwargs):
        self._shutdown_requested = False
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def transition_state(self, *args, **kwargs):
        raise NotImplementedError("StateManager.transition_state must be implemented by subclasses")


class ReconnectionHandler(ShutdownRequestMixin):
    """Handles reconnect operations."""

    def __init__(self, *args, **kwargs):
        self._shutdown_requested = False
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def reconnect(self, *args, **kwargs):
        raise NotImplementedError("ReconnectionHandler.reconnect must be implemented by subclasses")


class HealthMonitor(ShutdownRequestMixin):
    """Handles monitor operations."""

    def __init__(self, *args, **kwargs):
        self._shutdown_requested = False
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def monitor(self, *args, **kwargs):
        return None


class NotificationManager(ShutdownRequestMixin):
    """Handles notify operations."""

    def __init__(self, *args, **kwargs):
        self._shutdown_requested = False
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def notify(self, *args, **kwargs):
        raise NotImplementedError("Subclasses must override notify()")
