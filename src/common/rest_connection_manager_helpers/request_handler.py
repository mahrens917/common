"""
RequestHandler for rest_connection_manager
"""

import logging

from ..connection_manager_helpers.shutdown_mixin import ShutdownRequestMixin

logger = logging.getLogger(__name__)


class RequestHandler(ShutdownRequestMixin):
    """
    Handles handle_request operations
    """

    def __init__(self, *args, **kwargs):
        """Initialize RequestHandler"""
        self._shutdown_requested = False
        # Store passed dependencies
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def handle_request(self, *args, **kwargs):
        """
        Main operation method - must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement handle_request()")
