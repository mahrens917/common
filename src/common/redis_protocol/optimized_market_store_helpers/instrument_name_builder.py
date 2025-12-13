"""
Instrument name construction for OptimizedMarketStore
"""

import re
from datetime import datetime
from typing import Optional

from ...redis_schema import DeribitInstrumentDescriptor, DeribitInstrumentType


class InstrumentNameBuilder:
    """Constructs canonical instrument names from descriptors"""

    @staticmethod
    def _resolve_expiry_token(descriptor: DeribitInstrumentDescriptor) -> str:
        """
        Convert descriptor expiry metadata into a canonical Deribit-style token.

        Returns:
            Expiry token formatted as DDMMMYY (e.g. 25AUG24) when possible.
            Falls back to the descriptor token or ISO fragment when parsing fails.
        """

        expiry_token = getattr(descriptor, "expiry_token", None)
        if not expiry_token:
            expiry_token = getattr(descriptor, "expiry_iso", None)
        if expiry_token is None:
            token = ""
        else:
            token = str(expiry_token)
        token = token.strip()
        if not token:
            return "NA"

        uppercase = token.upper()
        if re.fullmatch(r"\d{2}[A-Z]{3}\d{2}", uppercase):
            return uppercase

        # Attempt to parse YYYY-MM-DD formats.
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                dt = datetime.strptime(token, fmt)
                return dt.strftime("%d%b%y").upper()
            except ValueError:  # policy_guard: allow-silent-handler
                continue

        try:
            dt = datetime.fromisoformat(token)
            return dt.strftime("%d%b%y").upper()
        except ValueError:  # policy_guard: allow-silent-handler
            return uppercase

    @staticmethod
    def _format_strike_value(strike: Optional[float]) -> str:
        """Render a strike value with stable formatting."""
        if strike is None:
            _none_guard_value = "NA"
            return _none_guard_value
        if float(strike).is_integer():
            return str(int(strike))
        return f"{strike:.8f}".rstrip("0").rstrip(".")

    @staticmethod
    def derive_instrument_name(
        descriptor: DeribitInstrumentDescriptor,
        *,
        strike_value: Optional[float],
        option_type: Optional[str],
    ) -> str:
        """Construct a canonical instrument name without relying on retired helpers."""
        base_currency_raw = descriptor.currency
        if base_currency_raw in (None, ""):
            raise ValueError("Descriptor missing base currency")
        base_currency = str(base_currency_raw).upper()

        if descriptor.instrument_type == DeribitInstrumentType.SPOT:
            quote_candidate = descriptor.quote_currency
            if not quote_candidate:
                quote_candidate = "USD"
            quote = str(quote_candidate).upper()
            return f"{base_currency}-{quote}"

        expiry_token = InstrumentNameBuilder._resolve_expiry_token(descriptor)

        if descriptor.instrument_type == DeribitInstrumentType.FUTURE:
            return f"{base_currency}-{expiry_token}"

        option_side_source = ""
        if isinstance(descriptor.option_kind, str) and descriptor.option_kind:
            option_side_source = descriptor.option_kind.lower()
        elif option_type:
            option_side_source = option_type.lower()

        if option_side_source.startswith("c"):
            suffix = "C"
        else:
            suffix = "P"
        strike_component = InstrumentNameBuilder._format_strike_value(strike_value)
        return f"{base_currency}-{expiry_token}-{strike_component}-{suffix}"
