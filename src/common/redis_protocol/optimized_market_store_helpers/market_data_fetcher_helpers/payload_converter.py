"""Market payload data conversion logic."""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PayloadConverter:
    """Converts Redis market payloads to typed dictionaries."""

    @staticmethod
    def convert_market_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert raw Redis hash data to typed market payload.

        Args:
            raw: Raw Redis hash data

        Returns:
            Converted payload with proper types
        """
        result: Dict[str, Any] = {}
        for field, value in raw.items():
            if isinstance(value, bytes):
                value = value.decode("utf-8", "ignore")

            if field == "last_update":
                result[field] = value
                continue

            text = str(value)
            try:
                if any(sep in text for sep in (".", "e", "E")):
                    result[field] = float(text)
                else:
                    result[field] = int(text)
            except (  # policy_guard: allow-silent-handler
                TypeError,
                ValueError,
            ):
                result[field] = value

        return result
