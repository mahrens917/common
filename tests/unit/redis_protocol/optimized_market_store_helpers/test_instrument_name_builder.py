"""Tests for instrument_name_builder module."""

from __future__ import annotations

from dataclasses import replace

import pytest

from src.common.redis_protocol.optimized_market_store_helpers.instrument_name_builder import (
    InstrumentNameBuilder,
)
from src.common.redis_schema import DeribitInstrumentDescriptor, DeribitInstrumentType


def _create_descriptor(**overrides) -> DeribitInstrumentDescriptor:
    """Create a descriptor with sensible values for testing."""
    base = DeribitInstrumentDescriptor(
        key="markets:deribit:option:btc:2024-08-25:25000:c",
        instrument_type=DeribitInstrumentType.OPTION,
        currency="btc",
        expiry_iso="2024-08-25",
        expiry_token="25AUG24",
        strike="25000",
        option_kind="c",
        quote_currency="usd",
    )
    return replace(base, **overrides)


class TestResolveExpiryToken:
    """Tests for _resolve_expiry_token static method."""

    def test_returns_uppercase_when_already_in_correct_format(self) -> None:
        """Returns uppercase expiry token when already in DDMMMYY format."""
        descriptor = _create_descriptor(expiry_token="25aug24")
        result = InstrumentNameBuilder._resolve_expiry_token(descriptor)
        assert result == "25AUG24"

    def test_returns_uppercase_for_valid_expiry_token(self) -> None:
        """Returns uppercase token for valid DDMMMYY format."""
        descriptor = _create_descriptor(expiry_token="01DEC24")
        result = InstrumentNameBuilder._resolve_expiry_token(descriptor)
        assert result == "01DEC24"

    def test_parses_yyyy_mm_dd_format(self) -> None:
        """Parses YYYY-MM-DD ISO date format."""
        descriptor = _create_descriptor(expiry_token=None, expiry_iso="2024-12-31")
        result = InstrumentNameBuilder._resolve_expiry_token(descriptor)
        assert result == "31DEC24"

    def test_parses_iso_format_with_time(self) -> None:
        """Parses ISO datetime format with time component."""
        descriptor = _create_descriptor(expiry_token="2024-08-25T16:00:00", expiry_iso=None)
        result = InstrumentNameBuilder._resolve_expiry_token(descriptor)
        assert result == "25AUG24"

    def test_parses_iso_format_with_timezone(self) -> None:
        """Parses ISO datetime format with timezone."""
        descriptor = _create_descriptor(expiry_token="2024-08-25T16:00:00+0000", expiry_iso=None)
        result = InstrumentNameBuilder._resolve_expiry_token(descriptor)
        assert result == "25AUG24"

    def test_uses_fromisoformat_for_complex_dates(self) -> None:
        """Uses datetime.fromisoformat for complex date formats."""
        descriptor = _create_descriptor(expiry_token="2024-08-25T16:00:00.123456", expiry_iso=None)
        result = InstrumentNameBuilder._resolve_expiry_token(descriptor)
        assert result == "25AUG24"

    def test_returns_na_for_none_expiry_token(self) -> None:
        """Returns NA when expiry_token is None."""
        descriptor = _create_descriptor(expiry_token=None, expiry_iso=None)
        result = InstrumentNameBuilder._resolve_expiry_token(descriptor)
        assert result == "NA"

    def test_returns_na_for_empty_string_expiry_token(self) -> None:
        """Returns NA when expiry_token is empty string."""
        descriptor = _create_descriptor(expiry_token="", expiry_iso=None)
        result = InstrumentNameBuilder._resolve_expiry_token(descriptor)
        assert result == "NA"

    def test_returns_na_for_whitespace_only_expiry_token(self) -> None:
        """Returns NA when expiry_token is whitespace only."""
        descriptor = _create_descriptor(expiry_token="   ", expiry_iso=None)
        result = InstrumentNameBuilder._resolve_expiry_token(descriptor)
        assert result == "NA"

    def test_falls_back_to_expiry_iso_when_token_missing(self) -> None:
        """Falls back to expiry_iso when expiry_token is missing."""
        descriptor = _create_descriptor(expiry_token=None, expiry_iso="2024-08-25")
        result = InstrumentNameBuilder._resolve_expiry_token(descriptor)
        assert result == "25AUG24"

    def test_returns_uppercase_for_unparseable_format(self) -> None:
        """Returns uppercase string when format cannot be parsed."""
        descriptor = _create_descriptor(expiry_token="invalid-date-format", expiry_iso=None)
        result = InstrumentNameBuilder._resolve_expiry_token(descriptor)
        assert result == "INVALID-DATE-FORMAT"

    def test_handles_numeric_expiry_token(self) -> None:
        """Handles numeric expiry tokens by parsing as ISO date."""
        descriptor = _create_descriptor(expiry_token="2024-08-25", expiry_iso=None)
        result = InstrumentNameBuilder._resolve_expiry_token(descriptor)
        assert result == "25AUG24"

    def test_strips_whitespace_from_token(self) -> None:
        """Strips whitespace from expiry token before processing."""
        descriptor = _create_descriptor(expiry_token="  25AUG24  ", expiry_iso=None)
        result = InstrumentNameBuilder._resolve_expiry_token(descriptor)
        assert result == "25AUG24"


class TestFormatStrikeValue:
    """Tests for _format_strike_value static method."""

    def test_returns_na_for_none(self) -> None:
        """Returns NA when strike is None."""
        result = InstrumentNameBuilder._format_strike_value(None)
        assert result == "NA"

    def test_formats_integer_strike_as_int(self) -> None:
        """Formats integer strike values without decimal point."""
        result = InstrumentNameBuilder._format_strike_value(25000.0)
        assert result == "25000"

    def test_formats_zero_as_int(self) -> None:
        """Formats zero strike as integer."""
        result = InstrumentNameBuilder._format_strike_value(0.0)
        assert result == "0"

    def test_formats_float_with_precision(self) -> None:
        """Formats float strike values with appropriate precision."""
        result = InstrumentNameBuilder._format_strike_value(123.456)
        assert result == "123.456"

    def test_strips_trailing_zeros(self) -> None:
        """Strips trailing zeros from float values."""
        result = InstrumentNameBuilder._format_strike_value(123.4500)
        assert result == "123.45"

    def test_strips_trailing_decimal_point(self) -> None:
        """Strips trailing decimal point when no fractional part remains."""
        result = InstrumentNameBuilder._format_strike_value(123.0)
        assert result == "123"

    def test_formats_very_small_numbers(self) -> None:
        """Formats very small decimal numbers correctly."""
        result = InstrumentNameBuilder._format_strike_value(0.00000001)
        assert result == "0.00000001"

    def test_formats_large_numbers(self) -> None:
        """Formats large numbers correctly."""
        result = InstrumentNameBuilder._format_strike_value(1000000.0)
        assert result == "1000000"

    def test_formats_negative_numbers(self) -> None:
        """Formats negative numbers correctly."""
        result = InstrumentNameBuilder._format_strike_value(-123.45)
        assert result == "-123.45"

    def test_handles_scientific_notation_conversion(self) -> None:
        """Handles numbers that might be in scientific notation."""
        result = InstrumentNameBuilder._format_strike_value(1.23e-5)
        assert result == "0.0000123"

    def test_truncates_to_8_decimal_places(self) -> None:
        """Truncates to maximum 8 decimal places."""
        result = InstrumentNameBuilder._format_strike_value(123.123456789)
        assert result == "123.12345679"


class TestDeriveInstrumentName:
    """Tests for derive_instrument_name static method."""

    def test_derives_spot_instrument_name_with_quote(self) -> None:
        """Derives spot instrument name with quote currency."""
        descriptor = _create_descriptor(
            instrument_type=DeribitInstrumentType.SPOT, quote_currency="USD"
        )
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=None, option_type=None
        )
        assert result == "BTC-USD"

    def test_derives_spot_instrument_name_without_quote(self) -> None:
        """Derives spot instrument name without quote currency (uses USD)."""
        descriptor = _create_descriptor(
            instrument_type=DeribitInstrumentType.SPOT, quote_currency=None
        )
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=None, option_type=None
        )
        assert result == "BTC-USD"

    def test_derives_spot_instrument_name_with_empty_quote(self) -> None:
        """Derives spot instrument name with empty quote currency (uses USD)."""
        descriptor = _create_descriptor(
            instrument_type=DeribitInstrumentType.SPOT, quote_currency=""
        )
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=None, option_type=None
        )
        assert result == "BTC-USD"

    def test_derives_future_instrument_name(self) -> None:
        """Derives future instrument name with expiry."""
        descriptor = _create_descriptor(instrument_type=DeribitInstrumentType.FUTURE)
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=None, option_type=None
        )
        assert result == "BTC-25AUG24"

    def test_derives_call_option_name_from_descriptor(self) -> None:
        """Derives call option name using descriptor option_kind."""
        descriptor = _create_descriptor(option_kind="call", strike="50000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type=None
        )
        assert result == "BTC-25AUG24-50000-C"

    def test_derives_put_option_name_from_descriptor(self) -> None:
        """Derives put option name using descriptor option_kind."""
        descriptor = _create_descriptor(option_kind="put", strike="50000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type=None
        )
        assert result == "BTC-25AUG24-50000-P"

    def test_derives_call_option_name_from_parameter(self) -> None:
        """Derives call option name using option_type parameter."""
        descriptor = _create_descriptor(option_kind=None, strike="50000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type="call"
        )
        assert result == "BTC-25AUG24-50000-C"

    def test_derives_put_option_name_from_parameter(self) -> None:
        """Derives put option name using option_type parameter."""
        descriptor = _create_descriptor(option_kind=None, strike="50000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type="put"
        )
        assert result == "BTC-25AUG24-50000-P"

    def term_prefers_descriptor_option_kind_over_parameter(self) -> None:
        """Prefers descriptor option_kind over option_type parameter."""
        descriptor = _create_descriptor(option_kind="call", strike="50000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type="put"
        )
        assert result == "BTC-25AUG24-50000-C"

    def test_handles_option_kind_with_c_prefix(self) -> None:
        """Handles option_kind starting with 'c' as call."""
        descriptor = _create_descriptor(option_kind="c", strike="50000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type=None
        )
        assert result == "BTC-25AUG24-50000-C"

    def test_handles_option_kind_with_p_prefix(self) -> None:
        """Handles option_kind starting with 'p' as put."""
        descriptor = _create_descriptor(option_kind="p", strike="50000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type=None
        )
        assert result == "BTC-25AUG24-50000-P"

    def test_handles_non_call_option_as_put(self) -> None:
        """Treats non-call options as puts."""
        descriptor = _create_descriptor(option_kind="xyz", strike="50000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type=None
        )
        assert result == "BTC-25AUG24-50000-P"

    def test_handles_empty_option_kind_as_put(self) -> None:
        """Handles empty option_kind as put."""
        descriptor = _create_descriptor(option_kind="", strike="50000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type=None
        )
        assert result == "BTC-25AUG24-50000-P"

    def test_handles_none_strike_value(self) -> None:
        """Handles None strike value in option name."""
        descriptor = _create_descriptor(option_kind="call", strike=None)
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=None, option_type=None
        )
        assert result == "BTC-25AUG24-NA-C"

    def test_handles_float_strike_value(self) -> None:
        """Handles float strike value in option name."""
        descriptor = _create_descriptor(option_kind="call", strike="123.456")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=123.456, option_type=None
        )
        assert result == "BTC-25AUG24-123.456-C"

    def test_converts_currency_to_uppercase(self) -> None:
        """Converts currency to uppercase in output."""
        descriptor = _create_descriptor(
            currency="eth", instrument_type=DeribitInstrumentType.FUTURE
        )
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=None, option_type=None
        )
        assert result == "ETH-25AUG24"

    def test_converts_quote_currency_to_uppercase(self) -> None:
        """Converts quote currency to uppercase for spot."""
        descriptor = _create_descriptor(
            instrument_type=DeribitInstrumentType.SPOT, quote_currency="usdt"
        )
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=None, option_type=None
        )
        assert result == "BTC-USDT"

    def test_raises_valueerror_for_none_currency(self) -> None:
        """Raises ValueError when currency is None."""
        descriptor = _create_descriptor(currency=None)
        with pytest.raises(ValueError, match="Descriptor missing base currency"):
            InstrumentNameBuilder.derive_instrument_name(
                descriptor, strike_value=None, option_type=None
            )

    def test_raises_valueerror_for_empty_currency(self) -> None:
        """Raises ValueError when currency is empty string."""
        descriptor = _create_descriptor(currency="")
        with pytest.raises(ValueError, match="Descriptor missing base currency"):
            InstrumentNameBuilder.derive_instrument_name(
                descriptor, strike_value=None, option_type=None
            )


class TestInstrumentNameBuilderIntegration:
    """Integration tests covering complete workflows."""

    def test_complete_btc_call_option_workflow(self) -> None:
        """Complete workflow for BTC call option."""
        descriptor = _create_descriptor(
            currency="btc",
            expiry_iso="2024-12-27",
            expiry_token="27DEC24",
            strike="60000",
            option_kind="call",
        )
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=60000.0, option_type=None
        )
        assert result == "BTC-27DEC24-60000-C"

    def test_complete_eth_put_option_workflow(self) -> None:
        """Complete workflow for ETH put option."""
        descriptor = _create_descriptor(
            currency="eth",
            expiry_iso="2025-01-31",
            expiry_token="31JAN25",
            strike="3500.5",
            option_kind="put",
        )
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=3500.5, option_type=None
        )
        assert result == "ETH-31JAN25-3500.5-P"

    def test_complete_spot_workflow_with_stablecoin(self) -> None:
        """Complete workflow for spot trading pair with stablecoin."""
        descriptor = _create_descriptor(
            instrument_type=DeribitInstrumentType.SPOT, currency="btc", quote_currency="usdc"
        )
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=None, option_type=None
        )
        assert result == "BTC-USDC"

    def test_complete_future_workflow_near_expiry(self) -> None:
        """Complete workflow for future near expiry."""
        descriptor = _create_descriptor(
            instrument_type=DeribitInstrumentType.FUTURE,
            currency="btc",
            expiry_iso="2024-12-31",
            expiry_token="31DEC24",
        )
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=None, option_type=None
        )
        assert result == "BTC-31DEC24"

    def test_workflow_with_parsed_iso_date(self) -> None:
        """Workflow with ISO date that needs parsing."""
        descriptor = _create_descriptor(
            instrument_type=DeribitInstrumentType.FUTURE,
            expiry_token=None,
            expiry_iso="2025-03-28",
        )
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=None, option_type=None
        )
        assert result == "BTC-28MAR25"

    def test_workflow_with_fractional_strike(self) -> None:
        """Workflow with fractional strike price."""
        descriptor = _create_descriptor(
            option_kind="c", strike="2500.125", expiry_token="15JUN24", expiry_iso="2024-06-15"
        )
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=2500.125, option_type=None
        )
        assert result == "BTC-15JUN24-2500.125-C"

    def test_workflow_handles_case_insensitive_option_type(self) -> None:
        """Workflow handles case-insensitive option type parameter."""
        descriptor = _create_descriptor(option_kind=None, strike="50000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type="CALL"
        )
        assert result == "BTC-25AUG24-50000-C"

    def test_workflow_with_very_large_strike(self) -> None:
        """Workflow with very large strike value."""
        descriptor = _create_descriptor(option_kind="call", strike="1000000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=1000000.0, option_type=None
        )
        assert result == "BTC-25AUG24-1000000-C"

    def test_workflow_with_very_small_strike(self) -> None:
        """Workflow with very small strike value."""
        descriptor = _create_descriptor(option_kind="put", strike="0.001")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=0.001, option_type=None
        )
        assert result == "BTC-25AUG24-0.001-P"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_handles_whitespace_in_option_kind(self) -> None:
        """Handles whitespace in option_kind field (not stripped, treated as put)."""
        descriptor = _create_descriptor(option_kind="  call  ", strike="50000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type=None
        )
        # Whitespace prevents startswith('c') check, so treated as put
        assert result == "BTC-25AUG24-50000-P"

    def test_handles_mixed_case_currency(self) -> None:
        """Handles mixed case currency codes."""
        descriptor = _create_descriptor(
            currency="BtC", instrument_type=DeribitInstrumentType.FUTURE
        )
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=None, option_type=None
        )
        assert result == "BTC-25AUG24"

    def test_handles_expiry_with_microseconds(self) -> None:
        """Handles expiry dates with microsecond precision."""
        descriptor = _create_descriptor(expiry_token="2024-08-25T16:00:00.123456", expiry_iso=None)
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type="call"
        )
        assert result == "BTC-25AUG24-50000-C"

    def test_handles_zero_strike_option(self) -> None:
        """Handles option with zero strike."""
        descriptor = _create_descriptor(option_kind="call", strike="0")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=0.0, option_type=None
        )
        assert result == "BTC-25AUG24-0-C"

    def test_handles_negative_strike(self) -> None:
        """Handles negative strike values."""
        descriptor = _create_descriptor(option_kind="put", strike="-100")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=-100.0, option_type=None
        )
        assert result == "BTC-25AUG24--100-P"

    def test_handles_option_type_with_full_word_call(self) -> None:
        """Handles option_type with full word 'call'."""
        descriptor = _create_descriptor(option_kind=None, strike="50000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type="call"
        )
        assert result == "BTC-25AUG24-50000-C"

    def test_handles_option_type_with_full_word_put(self) -> None:
        """Handles option_type with full word 'put'."""
        descriptor = _create_descriptor(option_kind=None, strike="50000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type="put"
        )
        assert result == "BTC-25AUG24-50000-P"

    def test_handles_option_type_with_single_letter_c(self) -> None:
        """Handles option_type with single letter 'c'."""
        descriptor = _create_descriptor(option_kind=None, strike="50000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type="c"
        )
        assert result == "BTC-25AUG24-50000-C"

    def test_handles_option_type_with_single_letter_p(self) -> None:
        """Handles option_type with single letter 'p'."""
        descriptor = _create_descriptor(option_kind=None, strike="50000")
        result = InstrumentNameBuilder.derive_instrument_name(
            descriptor, strike_value=50000.0, option_type="p"
        )
        assert result == "BTC-25AUG24-50000-P"

    def test_handles_unicode_in_unparsable_expiry(self) -> None:
        """Handles unicode characters in unparsable expiry token."""
        descriptor = _create_descriptor(expiry_token="invalid™date®", expiry_iso=None)
        result = InstrumentNameBuilder._resolve_expiry_token(descriptor)
        assert result == "INVALID™DATE®"
