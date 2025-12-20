"""Extract and validate delta message fields."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import orjson

logger = logging.getLogger(__name__)


class DeltaFieldExtractor:
    """Extracts and validates fields from delta messages."""

    @staticmethod
    def extract_fields(
        msg_data: Dict[str, Any],
    ) -> tuple[Optional[str], Optional[float], Optional[float]]:
        """Extract and validate delta message fields."""
        from .field_converter import FieldConverter

        side = FieldConverter.string_or_default(msg_data.get("side")).lower()
        price = msg_data.get("price")
        delta = msg_data.get("delta")

        if None in (side, price, delta):
            logger.error("Invalid delta message structure: %s", orjson.dumps(msg_data).decode())
            return None, None, None

        if not isinstance(price, (int, float)) or not isinstance(delta, (int, float)):
            logger.error(
                "Invalid numeric types: price=%r (type=%s), delta=%r (type=%s)",
                price,
                type(price),
                delta,
                type(delta),
            )
            return None, None, None

        return side, price, delta

    @staticmethod
    def convert_side_and_price(side: str, price: float) -> tuple[Optional[str], Optional[str]]:
        """Convert side and price to orderbook fields."""
        if side == "yes":
            return "yes_bids", str(price)
        if side == "no":
            converted_price = 100 - float(price)
            return "yes_asks", str(converted_price)

        logger.error("Unknown side in delta message: %s", side)
        return None, None
