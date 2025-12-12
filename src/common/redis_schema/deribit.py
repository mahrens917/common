from __future__ import annotations

"""Deribit-related Redis key utilities for the unified schema."""


from typing import Optional

from .markets import (
    DeribitInstrumentDescriptor,
    DeribitInstrumentKey,
    DeribitInstrumentType,
)

# Constants
_CONST_4 = 4
_CONST_5 = 5
_CONST_7 = 7


def parse_deribit_market_key(key: str | bytes) -> DeribitInstrumentDescriptor:
    """Convert a Deribit market Redis key into a structured descriptor."""
    if isinstance(key, bytes):
        try:
            key = key.decode("utf-8")
        except UnicodeDecodeError as exc:  # policy_guard: allow-silent-handler
            raise TypeError("Deribit key must be valid UTF-8 bytes.") from exc

    parts = _split_and_validate_key(key)
    instrument_type = _parse_instrument_type(parts)
    currency = parts[3].upper()

    expiry_iso, expiry_token, strike, option_kind, quote_currency = _parse_instrument_segments(key, parts, instrument_type)

    descriptor = DeribitInstrumentDescriptor(
        key=key,
        instrument_type=instrument_type,
        currency=currency,
        expiry_iso=expiry_iso,
        expiry_token=expiry_token,
        strike=strike,
        option_kind=option_kind,
        quote_currency=quote_currency,
    )

    _validate_normalized_key(descriptor, key)
    return descriptor


def _split_and_validate_key(key: str | bytes) -> list[str]:
    """Split the key and ensure it matches the expected namespace."""
    if isinstance(key, bytes):
        try:
            key = key.decode("utf-8")
        except UnicodeDecodeError as exc:  # policy_guard: allow-silent-handler
            raise TypeError("Deribit key must be valid UTF-8 bytes.") from exc

    if not key or not key.strip():
        raise ValueError("Key must be a non-empty string")

    parts = key.split(":")
    if len(parts) < _CONST_4:
        raise ValueError(f"Unexpected Deribit key format: {key!r}")

    if parts[0] != "markets" or parts[1] != "deribit":
        raise ValueError(f"Key is not within the Deribit markets namespace: {key!r}")
    return parts


def _parse_instrument_type(parts: list[str]) -> DeribitInstrumentType:
    """Parse and validate the instrument type segment."""
    instrument_type_value = parts[2]
    try:
        return DeribitInstrumentType(instrument_type_value)
    except ValueError as exc:  # policy_guard: allow-silent-handler
        raise ValueError(f"Unsupported Deribit instrument type '{instrument_type_value}' in {':'.join(parts)!r}") from exc


def _parse_instrument_segments(
    key: str, parts: list[str], instrument_type: DeribitInstrumentType
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Parse expiry/strike/option-specific segments."""
    expiry_iso: Optional[str] = None
    expiry_token: Optional[str] = None
    strike: Optional[str] = None
    option_kind: Optional[str] = None
    quote_currency: Optional[str] = None

    if instrument_type == DeribitInstrumentType.SPOT:
        quote_currency = _parse_spot_quote_currency(key, parts)
    elif instrument_type == DeribitInstrumentType.FUTURE:
        expiry_iso, expiry_token = _parse_future_segments(key, parts)
    elif instrument_type == DeribitInstrumentType.OPTION:
        expiry_iso, expiry_token, strike, option_kind = _parse_option_segments(key, parts)

    return expiry_iso, expiry_token, strike, option_kind, quote_currency


def _parse_spot_quote_currency(key: str, parts: list[str]) -> str:
    if len(parts) != _CONST_5:
        raise ValueError(f"Spot key must include quote currency: {key!r}")
    return parts[4].upper()


def _parse_future_segments(key: str, parts: list[str]) -> tuple[Optional[str], Optional[str]]:
    if len(parts) < _CONST_5:
        raise ValueError(f"Future key must include expiry segment: {key!r}")
    expiry_token = parts[4]
    return expiry_token, expiry_token


def _parse_option_segments(key: str, parts: list[str]) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    if len(parts) < _CONST_7:
        raise ValueError(f"Option key must include expiry, strike, and type: {key!r}")
    expiry_iso = parts[4]
    strike = parts[5]
    option_kind = parts[6]
    return expiry_iso, expiry_iso, strike, option_kind


def _validate_normalized_key(descriptor: DeribitInstrumentDescriptor, original_key: str | bytes) -> None:
    """Ensure the descriptor re-serializes to the same key."""
    if isinstance(original_key, bytes):
        try:
            original_key = original_key.decode("utf-8")
        except UnicodeDecodeError as exc:  # policy_guard: allow-silent-handler
            raise TypeError("Deribit key must be valid UTF-8 bytes.") from exc

    expected_key = DeribitInstrumentKey(
        instrument_type=descriptor.instrument_type,
        currency=descriptor.currency,
        expiry_iso=descriptor.expiry_iso,
        strike=descriptor.strike,
        option_kind=descriptor.option_kind,
        quote_currency=descriptor.quote_currency,
    ).key()

    if expected_key != original_key:
        raise ValueError(f"Deribit key {original_key!r} does not match normalized form {expected_key!r}")
