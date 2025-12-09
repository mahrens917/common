"""State processing and validation for ConnectionStateInfo."""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ...connection_state import ConnectionState
from ..error_types import JSON_ERRORS, SERIALIZATION_ERRORS

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStateInfo:
    """
    Connection state information for a service.

    Tracks detailed connection state including reconnection status,
    timing information, and error context for intelligent alert suppression.
    """

    service_name: str
    state: ConnectionState
    timestamp: float
    in_reconnection: bool
    reconnection_start_time: Optional[float] = None
    error_context: Optional[str] = None
    consecutive_failures: int = 0
    last_successful_connection: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service_name": self.service_name,
            "state": self.state.value,
            "timestamp": self.timestamp,
            "in_reconnection": self.in_reconnection,
            "reconnection_start_time": self.reconnection_start_time,
            "error_context": self.error_context,
            "consecutive_failures": self.consecutive_failures,
            "last_successful_connection": self.last_successful_connection,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Optional["ConnectionStateInfo"]:
        """Create from dictionary."""
        try:
            data = data.copy()
            data["state"] = ConnectionState(data["state"])
            return ConnectionStateInfo(**data)
        except (ValueError, KeyError, TypeError):
            logger.error("Failed to create ConnectionStateInfo from dict", exc_info=True)
            return None


def serialize_state_info(state_info: ConnectionStateInfo) -> Optional[str]:
    """Serialize state info to JSON string."""
    try:
        return json.dumps(state_info.to_dict())
    except SERIALIZATION_ERRORS:
        logger.error(
            "Failed to serialise connection state for %s",
            state_info.service_name,
            exc_info=True,
        )
        return None


def deserialize_state_json(service_name: str, state_json: str) -> Optional[ConnectionStateInfo]:
    """Deserialize state from JSON string."""
    try:
        data = json.loads(state_json)
        return ConnectionStateInfo.from_dict(data)
    except JSON_ERRORS:
        logger.error(
            "Failed to decode connection state payload for %s",
            service_name,
            exc_info=True,
        )
        return None
