"""
MessageHandler for websocket_connection_manager
"""

import logging

from ..connection_manager_helpers.shutdown_mixin import ShutdownRequestMixin

logger = logging.getLogger(__name__)


class MessageHandler(ShutdownRequestMixin):
    """
    Handles handle_message operations
    """

    def __init__(self, *args, **kwargs):
        """Initialize MessageHandler"""
        self._shutdown_requested = False
        # Store passed dependencies
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def handle_message(self, *args, **kwargs):
        """
        Main operation method
        """
        raise NotImplementedError("MessageHandler.handle_message not implemented")
