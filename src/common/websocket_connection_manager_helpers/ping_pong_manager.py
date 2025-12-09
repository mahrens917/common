"""
PingPongManager for websocket_connection_manager
"""

import logging

from ..connection_manager_helpers.shutdown_mixin import ShutdownRequestMixin

logger = logging.getLogger(__name__)


class PingPongManager(ShutdownRequestMixin):
    """
    Handles manage_ping_pong operations
    """

    def __init__(self, *args, **kwargs):
        """Initialize PingPongManager"""
        self._shutdown_requested = False
        # Store passed dependencies
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def manage_ping_pong(self, *args, **kwargs):
        """
        Main operation method
        """
        raise NotImplementedError("PingPongManager.manage_ping_pong not implemented")
