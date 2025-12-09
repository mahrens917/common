"""
ReconnectionHandler for connection_manager
"""

import logging

from .shutdown_mixin import ShutdownRequestMixin

logger = logging.getLogger(__name__)


class ReconnectionHandler(ShutdownRequestMixin):
    """
    Handles reconnect operations
    """

    def __init__(self, *args, **kwargs):
        """Initialize ReconnectionHandler"""
        self._shutdown_requested = False
        # Store passed dependencies
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def reconnect(self, *args, **kwargs):
        """
        Main operation method
        """
        raise NotImplementedError("ReconnectionHandler.reconnect must be implemented by subclasses")
