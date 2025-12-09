"""
StateManager for connection_manager
"""

import logging

from .shutdown_mixin import ShutdownRequestMixin

logger = logging.getLogger(__name__)


class StateManager(ShutdownRequestMixin):
    """
    Handles transition_state operations
    """

    def __init__(self, *args, **kwargs):
        """Initialize StateManager"""
        self._shutdown_requested = False
        # Store passed dependencies
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def transition_state(self, *args, **kwargs):
        """
        Main operation method
        """
        raise NotImplementedError("StateManager.transition_state must be implemented by subclasses")
