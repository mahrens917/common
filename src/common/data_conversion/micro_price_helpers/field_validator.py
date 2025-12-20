"""Field validation for micro price conversion."""

from __future__ import annotations

import logging
from typing import Optional

from ...data_models.instrument import Instrument
from .field_resolver import FieldResolver

logger = logging.getLogger(__name__)

# Required fields for micro price conversion
_REQUIRED_INSTRUMENT_FIELDS = ("best_bid", "best_ask", "strike", "option_type", "expiry")


class FieldValidator:
    """Validates required fields for micro price conversion."""

    @staticmethod
    def validate_required_fields(instrument: Instrument) -> None:
        """
        Validate that all required fields are present on the instrument.

        This is an object-attribute validator, distinct from the mapping-key
        validator in common.validation.required_fields.
        """
        symbol = FieldResolver.resolve_symbol_for_logging(instrument)
        missing_fields = [field for field in _REQUIRED_INSTRUMENT_FIELDS if getattr(instrument, field, None) is None]
        if missing_fields:
            field_list = ", ".join(missing_fields)
            raise ValueError(f"Instrument {symbol} missing required fields: {field_list}")

    @staticmethod
    def extract_prices_and_sizes(instrument: Instrument) -> tuple[float, float, float, float]:
        """Extract and validate prices and sizes from instrument."""
        symbol = FieldResolver.resolve_symbol_for_logging(instrument)
        best_bid = instrument.best_bid
        best_ask = instrument.best_ask
        if best_bid is None or best_ask is None:
            raise ValueError(f"Instrument {symbol} missing bid/ask prices: best_bid={best_bid}, best_ask={best_ask}")
        bid_price = float(best_bid)
        ask_price = float(best_ask)

        def _coerce_size(value: Optional[float], label: str) -> float:
            if value is None:
                instrument_name = FieldResolver.resolve_symbol_for_logging(instrument)
                raise ValueError(
                    "FAIL-FAST: Missing required {label} for instrument {name}. "
                    "Synthetic values are forbidden - all data must be sourced from the exchange.".format(label=label, name=instrument_name)
                )
            return float(value)

        bid_size = _coerce_size(getattr(instrument, "best_bid_size", None), "best_bid_size")
        ask_size = _coerce_size(getattr(instrument, "best_ask_size", None), "best_ask_size")
        return bid_price, ask_price, bid_size, ask_size
