"""Field resolution utilities for micro price conversion."""

import logging
from datetime import datetime, timezone

from common.exceptions import ValidationError

from ...data_models.instrument import Instrument

logger = logging.getLogger(__name__)


class FieldResolver:
    """Resolves fields from instrument objects."""

    @staticmethod
    def resolve_symbol_for_logging(instrument: Instrument) -> str:
        """Get symbol or instrument name for logging."""
        symbol = getattr(instrument, "symbol", None)
        if symbol:
            return str(symbol)

        instrument_name = getattr(instrument, "instrument_name", None)
        if instrument_name:
            return str(instrument_name)

        return "unknown"

    @staticmethod
    def resolve_instrument_name(instrument: Instrument) -> str:
        """Resolve instrument name from various fields."""
        instrument_name = getattr(instrument, "instrument_name", None)
        if instrument_name:
            return str(instrument_name)

        symbol = getattr(instrument, "symbol", None)
        if symbol:
            return str(symbol)

        raise ValidationError("Instrument lacks both instrument_name and symbol attributes required for micro " "price conversion.")

    @staticmethod
    def resolve_expiry_datetime(expiry_value: object) -> datetime:
        """Resolve expiry to datetime object."""
        if isinstance(expiry_value, int):
            return datetime.fromtimestamp(expiry_value, tz=timezone.utc)
        if isinstance(expiry_value, datetime):
            return expiry_value
        raise TypeError(f"Invalid expiry type: {type(expiry_value)}, expected int or datetime")

    @staticmethod
    def resolve_quote_timestamp(instrument: Instrument) -> datetime:
        """Resolve quote timestamp from instrument."""
        from ... import time_utils

        raw_timestamp = getattr(instrument, "quote_timestamp", None) or getattr(instrument, "mark_price_timestamp", None)
        if raw_timestamp is None:
            raw_timestamp = getattr(instrument, "timestamp", None)

        if isinstance(raw_timestamp, datetime):
            return raw_timestamp.replace(tzinfo=timezone.utc) if raw_timestamp.tzinfo is None else raw_timestamp.astimezone(timezone.utc)

        return time_utils.get_current_utc()
