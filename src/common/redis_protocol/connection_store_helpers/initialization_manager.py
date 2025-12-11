"""
Initialization management for ConnectionStore
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..connection_store import ConnectionStore

logger = logging.getLogger(__name__)


class InitializationManager:
    """Handles initialization of ConnectionStore components"""

    def __init__(self, parent: "ConnectionStore"):
        """
        Initialize manager

        Args:
            parent: Parent ConnectionStore instance
        """
        self._parent = parent

    async def ensure_initialized(self) -> None:
        """Ensure ConnectionStore is initialized with Redis and helpers"""
        if self._parent.redis_client is None:
            await self._initialize_redis()
        if not getattr(self._parent, "helpers_initialized", False):
            await self._initialize_helpers()
            self._parent.helpers_initialized = True

    async def _initialize_redis(self) -> None:
        """Initialize Redis connection using canonical implementation"""
        from ..connection_pool_core import get_redis_client

        self._parent.redis_client = await get_redis_client()
        logger.debug("Connection store initialized with Redis connection")

    async def _initialize_helpers(self) -> None:
        """Initialize helper managers"""
        from .metrics_manager import MetricsManager
        from .reconnection_event_manager import ReconnectionEventManager
        from .state_manager import StateManager

        redis_getter = self._parent.get_client

        self._parent.register_state_manager(StateManager(redis_getter, self._parent.connection_states_key))
        self._parent.register_metrics_manager(MetricsManager(redis_getter))
        self._parent.register_reconnection_event_manager(ReconnectionEventManager(redis_getter, self._parent.reconnection_events_key))
