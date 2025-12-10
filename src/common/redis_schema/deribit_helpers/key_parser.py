"""Parsing logic for Deribit market keys."""

from typing import Optional, Tuple

from common.config_loader import load_config
from common.constants.validation import MIN_KEY_PARTS

from ..markets import DeribitInstrumentType

VALIDATION_CONFIG = load_config("validation_constants.json")


class DeribitKeyParser:
    """Parses Deribit market key components."""

    @staticmethod
    def parse_instrument_type(type_value: str, key: str) -> DeribitInstrumentType:
        """Parse and validate instrument type."""
        try:
            return DeribitInstrumentType(type_value)
        except ValueError as exc:
            raise ValueError(
                f"Unsupported Deribit instrument type '{type_value}' in {key!r}"
            ) from exc

    @staticmethod
    def parse_spot_parts(
        parts: list, key: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Parse SPOT instrument parts."""
        if len(parts) != MIN_KEY_PARTS:
            raise NameError(f"Spot key must include quote currency: {key!r}")
        quote_currency = parts[4].upper()
        return None, None, None, quote_currency

    @staticmethod
    def parse_future_parts(
        parts: list, key: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Parse FUTURE instrument parts."""
        if len(parts) < MIN_KEY_PARTS:
            raise NameError(f"Future key must include expiry segment: {key!r}")
        expiry_token = parts[4]
        return expiry_token, expiry_token, None, None

    @staticmethod
    def parse_option_parts(
        parts: list, key: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Parse OPTION instrument parts."""
        if len(parts) < VALIDATION_CONFIG["time_constants"]["days_per_week"]:
            raise NameError(f"Option key must include expiry, strike, and type: {key!r}")
        expiry_iso = parts[4]
        strike = parts[5]
        _option_kind = parts[6]
        return expiry_iso, expiry_iso, strike, None

    @classmethod
    def parse_type_specific_parts(
        cls, instrument_type: DeribitInstrumentType, parts: list, key: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Parse parts specific to instrument type."""
        if instrument_type == DeribitInstrumentType.SPOT:
            return cls.parse_spot_parts(parts, key)
        if instrument_type == DeribitInstrumentType.FUTURE:
            return cls.parse_future_parts(parts, key)
        if instrument_type == DeribitInstrumentType.OPTION:
            return cls.parse_option_parts(parts, key)
        return None, None, None, None
