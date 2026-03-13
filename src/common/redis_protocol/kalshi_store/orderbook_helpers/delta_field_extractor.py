"""Extract and validate delta message fields."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import orjson

from common.redis_protocol.kalshi_store.utils_coercion import string_or_default

logger = logging.getLogger(__name__)

_CENTS_PER_DOLLAR = 100.0


def _extract_price_delta(
    msg_data: Dict[str, Any],
) -> tuple[Optional[float], Optional[float], bool]:
    """Extract price and delta from message, handling both legacy and dollar formats.

    Returns ``(price, delta, is_dollar_format)``.
    """
    price = msg_data.get("price")
    delta = msg_data.get("delta")
    is_dollar = False

    if price is None or delta is None:
        price_dollars = msg_data.get("price_dollars")
        delta_fp = msg_data.get("delta_fp")
        if price_dollars is not None and delta_fp is not None:
            if isinstance(price_dollars, (int, float)) and isinstance(delta_fp, (int, float)):
                return float(price_dollars), float(delta_fp), True
        return None, None, False

    if isinstance(price, (int, float)) and isinstance(delta, (int, float)):
        return float(price), float(delta), is_dollar
    return None, None, False


class DeltaFieldExtractor:
    """Extracts and validates fields from delta messages."""

    @staticmethod
    def extract_fields(
        msg_data: Dict[str, Any],
    ) -> tuple[Optional[str], Optional[float], Optional[float]]:
        """Extract and validate delta message fields.

        Handles both legacy (``price``/``delta``) and current dollar format
        (``price_dollars``/``delta_fp``).  Dollar prices are converted to cents.
        """
        side = string_or_default(msg_data.get("side")).lower()
        price, delta, is_dollar = _extract_price_delta(msg_data)

        if price is None or delta is None:
            logger.error("Invalid delta message structure: %s", orjson.dumps(msg_data).decode())
            return None, None, None

        if is_dollar:
            price = price * _CENTS_PER_DOLLAR

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
