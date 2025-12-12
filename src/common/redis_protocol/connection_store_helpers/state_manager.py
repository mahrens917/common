import logging
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ...connection_state import ConnectionState
from ..error_types import REDIS_ERRORS
from ..typing import ensure_awaitable
from .state_processor import (
    ConnectionStateInfo,
    deserialize_state_json,
    serialize_state_info,
)

logger = logging.getLogger(__name__)


class StateManager:
    def __init__(
        self,
        redis_getter: Callable[[], Awaitable[Any]],
        connection_states_key: str,
    ):
        self._get_client = redis_getter
        self.connection_states_key = connection_states_key

    async def store_connection_state(self, state_info: ConnectionStateInfo) -> bool:
        state_json = serialize_state_info(state_info)
        if state_json is None:
            return False
        client = await self._get_client()
        try:
            await ensure_awaitable(client.hset(self.connection_states_key, state_info.service_name, state_json))
            await ensure_awaitable(client.expire(self.connection_states_key, 86400))
            logger.debug(
                "Stored connection state for %s: %s",
                state_info.service_name,
                state_info.state.value,
            )
        except REDIS_ERRORS:  # policy_guard: allow-silent-handler
            logger.error(
                "Failed to store connection state for %s",
                state_info.service_name,
                exc_info=True,
            )
            return False
        else:
            return True

    async def get_connection_state(self, service_name: str) -> Optional[ConnectionStateInfo]:
        client = await self._get_client()
        try:
            state_json = await ensure_awaitable(client.hget(self.connection_states_key, service_name))
        except REDIS_ERRORS:  # policy_guard: allow-silent-handler
            logger.error("Failed to get connection state for %s", service_name, exc_info=True)
            return None
        if not state_json:
            logger.debug("No connection state found for %s", service_name)
            return None
        return deserialize_state_json(service_name, state_json)

    async def get_all_connection_states(self) -> Dict[str, ConnectionStateInfo]:
        client = await self._get_client()
        try:
            all_states = await ensure_awaitable(client.hgetall(self.connection_states_key))
        except REDIS_ERRORS:  # policy_guard: allow-silent-handler
            logger.error("Failed to get all connection states", exc_info=True)
            return {}
        result: Dict[str, ConnectionStateInfo] = {}
        for service_name, state_json in all_states.items():
            state_info = deserialize_state_json(service_name, state_json)
            if state_info:
                result[service_name] = state_info
        return result

    async def is_service_in_reconnection(self, service_name: str) -> bool:
        state_info = await self.get_connection_state(service_name)
        return state_info is not None and _is_reconnecting(state_info)

    async def get_services_in_reconnection(self) -> List[str]:
        all_states = await self.get_all_connection_states()
        return [service_name for service_name, state_info in all_states.items() if _is_reconnecting(state_info)]

    async def cleanup_stale_states(self, max_age_hours: int = 24) -> int:
        all_states = await self.get_all_connection_states()
        cutoff_time = time.time() - (max_age_hours * 3600)
        client = await self._get_client()
        cleaned_count = 0
        for service_name, state_info in all_states.items():
            if state_info.timestamp < cutoff_time:
                try:
                    await ensure_awaitable(client.hdel(self.connection_states_key, service_name))
                    logger.debug("Cleaned up stale connection state for %s", service_name)
                    cleaned_count += 1
                except REDIS_ERRORS:  # policy_guard: allow-silent-handler
                    logger.error(
                        "Failed to remove stale connection state for %s",
                        service_name,
                        exc_info=True,
                    )
        return cleaned_count


def _is_reconnecting(state_info: ConnectionStateInfo) -> bool:
    return state_info.in_reconnection or state_info.state in (
        ConnectionState.RECONNECTING,
        ConnectionState.CONNECTING,
    )
