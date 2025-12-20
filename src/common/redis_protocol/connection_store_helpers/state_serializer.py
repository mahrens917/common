"""State serialization helpers for StateManager."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from ...connection_state import ConnectionState
from ..error_types import JSON_ERRORS, PARSING_ERRORS, SERIALIZATION_ERRORS
from .state_manager import ConnectionStateInfo

logger = logging.getLogger(__name__)


def deserialize_state_info(service_name: str, state_json: str) -> Optional[ConnectionStateInfo]:
    """Deserialize JSON string to ConnectionStateInfo."""
    try:
        state_dict = json.loads(state_json)
    except JSON_ERRORS:  # policy_guard: allow-silent-handler
        logger.error(
            "Failed to decode connection state payload for %s",
            service_name,
            exc_info=True,
        )
        return None

    try:
        state_dict["state"] = ConnectionState(state_dict["state"])
    except SERIALIZATION_ERRORS:  # policy_guard: allow-silent-handler
        logger.error(
            "Failed to convert state '%s' to ConnectionState enum for %s",
            state_dict.get("state"),
            service_name,
            exc_info=True,
        )
        return None

    return ConnectionStateInfo(**state_dict)


def parse_all_states(all_states: Dict[str, Any]) -> Dict[str, ConnectionStateInfo]:
    """Parse all connection states from dict."""
    result: Dict[str, ConnectionStateInfo] = {}
    for service_name, state_json in all_states.items():
        try:
            state_dict = json.loads(state_json)
            state_dict["state"] = ConnectionState(state_dict["state"])
            result[service_name] = ConnectionStateInfo(**state_dict)
        except PARSING_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.warning(
                "Failed to parse connection state for %s: %s",
                service_name,
                exc,
            )
    return result
