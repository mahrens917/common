"""State query helpers for StateManager."""

from typing import List

from ...connection_state import ConnectionState
from .state_manager import ConnectionStateInfo


def is_reconnecting(state_info: ConnectionStateInfo) -> bool:
    """Check if service is in reconnection mode."""
    return state_info.in_reconnection or state_info.state in (
        ConnectionState.RECONNECTING,
        ConnectionState.CONNECTING,
    )


def filter_reconnecting_services(
    all_states: dict[str, ConnectionStateInfo],
) -> List[str]:
    """Filter services in reconnection from all states."""
    return [
        service_name
        for service_name, state_info in all_states.items()
        if is_reconnecting(state_info)
    ]
