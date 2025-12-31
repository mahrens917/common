from __future__ import annotations

from common.truthy import pick_if

"""Dataclasses describing market data keys."""


from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

from .namespaces import KeyBuilder, RedisNamespace, sanitize_segment
from .validators import register_namespace

register_namespace("markets:deribit:", "Live Deribit market snapshots")
register_namespace("markets:kalshi:", "Live Kalshi market snapshots")
register_namespace("reference:markets:", "Venue-agnostic market metadata")


class DeribitInstrumentType(str, Enum):
    """Supported Deribit instrument types."""

    OPTION = "option"
    FUTURE = "future"
    SPOT = "spot"


@dataclass(frozen=True)
class DeribitInstrumentKey:
    """Generate keys for Deribit instruments under the unified namespace."""

    instrument_type: DeribitInstrumentType
    currency: str
    expiry_iso: Optional[str] = None
    strike: Optional[str] = None
    option_kind: Optional[str] = None  # "c" or "p"
    quote_currency: Optional[str] = None

    def key(self) -> str:
        segments = ["deribit", self.instrument_type.value, sanitize_segment(self.currency)]
        if self.expiry_iso:
            segments.append(sanitize_segment(self.expiry_iso))
        if self.strike:
            segments.append(sanitize_segment(self.strike))
        if self.option_kind:
            segments.append(sanitize_segment(self.option_kind))
        if self.quote_currency:
            segments.append(sanitize_segment(self.quote_currency))
        builder = KeyBuilder(RedisNamespace.MARKETS, tuple(segments))
        return builder.render()


class KalshiMarketCategory(str, Enum):
    """High-level Kalshi market categories for namespacing."""

    BINARY = "binary"
    RANGE = "range"
    WEATHER = "weather"
    MACRO = "macro"
    CUSTOM = "custom"


@dataclass(frozen=True)
class KalshiMarketKey:
    """Generate keys for Kalshi markets."""

    category: KalshiMarketCategory
    ticker: str

    def key(self) -> str:
        segments = ["kalshi", self.category.value, sanitize_segment(self.ticker, case="upper")]
        builder = KeyBuilder(RedisNamespace.MARKETS, tuple(segments))
        return builder.render()


@dataclass(frozen=True)
class ReferenceMarketKey:
    """Key for cross-venue market metadata used by analytics pipelines."""

    venue: str
    ticker: str

    def key(self) -> str:
        segments = ["markets", sanitize_segment(self.venue), sanitize_segment(self.ticker)]
        builder = KeyBuilder(RedisNamespace.REFERENCE, tuple(segments))
        return builder.render()


@dataclass(frozen=True)
class DeribitInstrumentDescriptor:
    """Parsed representation of a Deribit ticker suitable for Redis storage."""

    key: str
    instrument_type: DeribitInstrumentType
    currency: str
    expiry_iso: Optional[str]
    expiry_token: Optional[str]
    strike: Optional[str]
    option_kind: Optional[str]
    quote_currency: Optional[str]

    def base_fields(self) -> Dict[str, str]:
        fields: Dict[str, str] = {
            "instrument_type": self.instrument_type.value,
            "currency": self.currency.upper(),
        }
        if self.expiry_iso:
            fields["expiry_iso"] = self.expiry_iso
        if self.expiry_token:
            fields["expiry_token"] = self.expiry_token
        if self.strike:
            fields["strike"] = self.strike
        if self.option_kind:
            fields["option_kind"] = self.option_kind
        if self.quote_currency:
            fields["quote_currency"] = self.quote_currency.upper()
        return fields

    @classmethod
    def from_instrument_data(
        cls,
        *,
        kind: str,
        base_currency: str,
        quote_currency: str,
        expiration_timestamp: Optional[int],
        strike: Optional[float],
        option_type: Optional[str],
    ) -> "DeribitInstrumentDescriptor":
        kind_normalized = kind.lower()
        try:
            instrument_type = DeribitInstrumentType(kind_normalized)
        except ValueError as exc:
            raise ValueError(f"Unsupported Deribit instrument kind: {kind}") from exc

        expiry_iso: Optional[str] = None
        expiry_token: Optional[str] = None
        strike_token: Optional[str] = None
        option_kind: Optional[str] = None
        quote = quote_currency

        if instrument_type == DeribitInstrumentType.SPOT:
            key = DeribitInstrumentKey(instrument_type, base_currency, quote_currency=quote_currency).key()
            return cls(key, instrument_type, base_currency, None, None, None, None, quote)

        if expiration_timestamp is None:
            raise ValueError("Deribit instrument missing expiration timestamp")

        expiry_dt = datetime.fromtimestamp(expiration_timestamp, tz=timezone.utc)
        expiry_iso = expiry_dt.date().isoformat()
        expiry_token = expiry_dt.strftime("%d%b%y").upper()

        if instrument_type == DeribitInstrumentType.FUTURE:
            key = DeribitInstrumentKey(instrument_type, base_currency, expiry_iso=expiry_iso).key()
            return cls(key, instrument_type, base_currency, expiry_iso, expiry_token, None, None, None)

        if strike is None:
            raise ValueError("Deribit option missing strike in instrument payload")
        if option_type is None:
            raise TypeError("Deribit option missing option_type in instrument payload")

        strike_token = cls._format_strike(strike)
        option_kind = pick_if(option_type.lower().startswith("c"), lambda: "c", lambda: "p")
        key = DeribitInstrumentKey(instrument_type, base_currency, expiry_iso, strike_token, option_kind).key()
        return cls(
            key,
            instrument_type,
            base_currency,
            expiry_iso,
            expiry_token,
            strike_token,
            option_kind,
            None,
        )

    @staticmethod
    def _format_strike(strike: float) -> str:
        if float(strike).is_integer():
            return str(int(strike))
        formatted = f"{strike:.8f}".rstrip("0").rstrip(".")
        if not formatted:
            return "0"
        return formatted
