"""
NotificationManager for connection_manager
"""

import logging

from .shutdown_mixin import ShutdownRequestMixin

logger = logging.getLogger(__name__)


class NotificationManager(ShutdownRequestMixin):
    """
    Handles notify operations
    """

    def __init__(self, *args, **kwargs):
        """Initialize NotificationManager"""
        self._shutdown_requested = False
        # Store passed dependencies
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def notify(self, *args, **kwargs):
        """
        Main operation method - stub that must be overridden by concrete classes.
        """
        raise NotImplementedError("Subclasses must override notify()")
