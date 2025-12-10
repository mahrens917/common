"""Tests for Deribit key validation helpers."""

import pytest

from common.redis_schema.deribit_helpers.key_validator import (
    VALIDATION_CONFIG,
    DeribitKeyValidator,
)
from common.redis_schema.markets import (
    DeribitInstrumentDescriptor,
    DeribitInstrumentKey,
    DeribitInstrumentType,
)


def test_validate_key_format_rejects_empty():
    with pytest.raises(TypeError):
        DeribitKeyValidator.validate_key_format("")


def test_validate_key_parts_raises_when_too_short(monkeypatch):
    monkeypatch.setitem(VALIDATION_CONFIG["field_counts"], "expected_parts", 5)
    with pytest.raises(TypeError, match="Unexpected Deribit key format"):
        DeribitKeyValidator.validate_key_parts(["markets", "deribit"], "markets:deribit")


def test_validate_namespace_rejects_other_namespace():
    with pytest.raises(ValueError, match="not within the Deribit"):
        DeribitKeyValidator.validate_namespace(["markets", "kalshi"], "markets:kalshi:ABC")


def test_validate_normalized_form_accepts_matching_key():
    key = DeribitInstrumentKey(
        DeribitInstrumentType.OPTION,
        currency="BTC",
        expiry_iso="2025-01-01",
        strike="300",
        option_kind="c",
    ).key()

    descriptor = DeribitInstrumentDescriptor(
        key=key,
        instrument_type=DeribitInstrumentType.OPTION,
        currency="BTC",
        expiry_iso="2025-01-01",
        expiry_token="01JAN25",
        strike="300",
        option_kind="c",
        quote_currency=None,
    )

    DeribitKeyValidator.validate_normalized_form(descriptor, key)


def test_validate_normalized_form_rejects_mismatch():
    key = DeribitInstrumentKey(
        DeribitInstrumentType.OPTION,
        currency="BTC",
        expiry_iso="2025-01-01",
        strike="300",
        option_kind="c",
    ).key()
    descriptor = DeribitInstrumentDescriptor(
        key=key,
        instrument_type=DeribitInstrumentType.OPTION,
        currency="BTC",
        expiry_iso="2025-01-01",
        expiry_token="01JAN25",
        strike="300",
        option_kind="c",
        quote_currency=None,
    )

    with pytest.raises(TypeError, match="does not match normalized form"):
        DeribitKeyValidator.validate_normalized_form(descriptor, "markets:deribit:option:BTC")
