"""Initialization logic for ConnectionStateTracker."""

import asyncio
import logging
from json import JSONDecodeError
from typing import Callable, Optional

from redis.exceptions import RedisError

from ..redis_protocol.connection_store import ConnectionStore, get_connection_store
from .error_builder import build_tracker_error
from .event_manager import EventManager
from .state_querier import StateQuerier
from .state_updater import StateUpdater

logger = logging.getLogger(__name__)

STORE_ERROR_TYPES = (
    ConnectionError,
    RedisError,
    RuntimeError,
    asyncio.TimeoutError,
    JSONDecodeError,
)


class TrackerInitializer:
    """Handles initialization of ConnectionStateTracker components."""

    @staticmethod
    async def initialize_components(
        connection_store: Optional[ConnectionStore],
        state_updater: Optional[StateUpdater],
        state_querier: Optional[StateQuerier],
        event_manager: Optional[EventManager],
        time_provider: Callable[[], float],
    ) -> tuple[ConnectionStore, StateUpdater, StateQuerier, EventManager]:
        """Initialize all tracker components if needed."""
        if connection_store is None:
            try:
                connection_store = await get_connection_store()
            except STORE_ERROR_TYPES as exc:
                raise build_tracker_error("Connection state tracker initialization failed", exc)
        # Initialize sub-components if not already done
        if state_updater is None:
            state_updater = StateUpdater(connection_store, time_provider)
            state_querier = StateQuerier(connection_store, time_provider)
            event_manager = EventManager(connection_store)
            logger.debug("Connection state tracker initialized")
        assert state_updater is not None
        assert state_querier is not None
        assert event_manager is not None
        return connection_store, state_updater, state_querier, event_manager

    @staticmethod
    def require_store(connection_store: Optional[ConnectionStore]) -> None:
        """Raise if connection store is not initialized."""
        if connection_store is None:
            raise RuntimeError("Connection store not initialized")
