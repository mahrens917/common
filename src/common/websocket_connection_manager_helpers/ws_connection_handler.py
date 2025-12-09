"""
WsConnectionHandler for websocket_connection_manager
"""

import logging

from ..connection_manager_helpers.shutdown_mixin import ShutdownRequestMixin

logger = logging.getLogger(__name__)


class WsConnectionHandler(ShutdownRequestMixin):
    """
    Handles handle_connection operations
    """

    def __init__(self, *args, **kwargs):
        """Initialize WsConnectionHandler"""
        self._shutdown_requested = False
        # Store passed dependencies
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def handle_connection(self, *args, **kwargs):
        """
        Main operation method
        """
        raise NotImplementedError("WsConnectionHandler.handle_connection not implemented")
