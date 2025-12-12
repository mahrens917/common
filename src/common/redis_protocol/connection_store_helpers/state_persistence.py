"""State persistence operations for StateManager."""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def try_serialize_state(state_dict: Dict[str, Any]) -> Optional[str]:
    """Attempt to serialize state dict to JSON."""
    try:
        return json.dumps(state_dict)
    except (TypeError, ValueError):  # policy_guard: allow-silent-handler
        logger.error("Failed to serialise state", exc_info=True)
        return None


def try_deserialize_state(state_json: str) -> Optional[Dict[str, Any]]:
    """Attempt to deserialize JSON string to dict."""
    try:
        return json.loads(state_json)
    except (json.JSONDecodeError, ValueError):  # policy_guard: allow-silent-handler
        logger.error("Failed to decode state JSON", exc_info=True)
        return None
