"""Tests for micro_price_helpers conversion module."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.common.data_models.micro_price_helpers.conversion import (
    MicroPriceConversionHelpers,
    determine_expiry,
    determine_underlying,
    extract_prices,
    extract_sizes,
    resolve_instrument_name,
    resolve_option_type,
    resolve_timestamp,
)
from src.common.data_models.micro_price_helpers.errors import OptionDataConversionError

DEFAULT_TEST_CONVERSION_BID_SIZE = 100
DEFAULT_TEST_CONVERSION_ASK_SIZE = 200
DEFAULT_TEST_CONVERSION_ALT_BID_SIZE = 50
DEFAULT_TEST_CONVERSION_ALT_ASK_SIZE = 75


class TestResolveInstrumentName:
    """Tests for resolve_instrument_name function."""

    def test_returns_instrument_name_from_attribute(self) -> None:
        """Returns instrument_name attribute value."""
        option = MagicMock()
        option.instrument_name = "BTC-25JAN24-50000-C"

        result = resolve_instrument_name(option)

        assert result == "BTC-25JAN24-50000-C"

    def test_returns_unknown_when_no_attribute(self) -> None:
        """Returns 'unknown' when no instrument_name attribute."""
        option = MagicMock(spec=[])

        result = resolve_instrument_name(option)

        assert result == "unknown"

    def test_returns_unknown_when_attribute_is_none(self) -> None:
        """Returns 'unknown' when instrument_name is None."""
        option = MagicMock()
        option.instrument_name = None

        result = resolve_instrument_name(option)

        assert result == "unknown"

    def test_returns_unknown_when_attribute_is_empty(self) -> None:
        """Returns 'unknown' when instrument_name is empty."""
        option = MagicMock()
        option.instrument_name = ""

        result = resolve_instrument_name(option)

        assert result == "unknown"


class TestDetermineUnderlying:
    """Tests for determine_underlying function."""

    def test_returns_underlying_from_attribute(self) -> None:
        """Returns underlying attribute value."""
        option = MagicMock()
        option.underlying = "BTC"

        result = determine_underlying(option, "BTC-25JAN24-50000-C")

        assert result == "BTC"

    def test_parses_btc_from_instrument_name(self) -> None:
        """Parses BTC from instrument name when no underlying attribute."""
        option = MagicMock()
        option.underlying = None

        result = determine_underlying(option, "BTC-25JAN24-50000-C")

        assert result == "BTC"

    def test_parses_eth_from_instrument_name(self) -> None:
        """Parses ETH from instrument name when no underlying attribute."""
        option = MagicMock()
        option.underlying = None

        result = determine_underlying(option, "ETH-25JAN24-3000-P")

        assert result == "ETH"

    def test_raises_when_cannot_determine(self) -> None:
        """Raises OptionDataConversionError when cannot determine underlying."""
        option = MagicMock()
        option.underlying = None

        with pytest.raises(OptionDataConversionError) as exc_info:
            determine_underlying(option, "unknown")

        assert "underlying" in str(exc_info.value)

    def test_raises_for_non_btc_eth_instrument(self) -> None:
        """Raises for instrument names not starting with BTC or ETH."""
        option = MagicMock()
        option.underlying = None

        with pytest.raises(OptionDataConversionError):
            determine_underlying(option, "SOL-25JAN24-100-C")


class TestDetermineExpiry:
    """Tests for determine_expiry function."""

    def test_returns_expiry_from_expiry_timestamp(self) -> None:
        """Returns expiry from expiry_timestamp attribute."""
        option = MagicMock()
        option.expiry_timestamp = 1706140800  # 2024-01-25 00:00:00 UTC

        result = determine_expiry(option)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 25
        assert result.tzinfo == timezone.utc

    def test_returns_expiry_from_datetime_expiry(self) -> None:
        """Returns expiry from datetime expiry attribute."""
        option = MagicMock(spec=["expiry"])
        option.expiry = datetime(2024, 1, 25, tzinfo=timezone.utc)

        result = determine_expiry(option)

        assert result == datetime(2024, 1, 25, tzinfo=timezone.utc)

    def test_raises_when_no_expiry(self) -> None:
        """Raises OptionDataConversionError when no expiry."""
        option = MagicMock(spec=[])

        with pytest.raises(OptionDataConversionError) as exc_info:
            determine_expiry(option)

        assert "expiry" in str(exc_info.value)

    def test_raises_when_expiry_timestamp_not_numeric(self) -> None:
        """Raises when expiry_timestamp is not numeric."""
        option = MagicMock()
        option.expiry_timestamp = "not-a-number"

        with pytest.raises(OptionDataConversionError) as exc_info:
            determine_expiry(option)

        assert "integer" in str(exc_info.value)


class TestResolveOptionType:
    """Tests for resolve_option_type function."""

    def test_returns_call_from_attribute(self) -> None:
        """Returns normalized call from option_type attribute."""
        option = MagicMock()
        option.option_type = "CALL"

        result = resolve_option_type(option)

        assert result == "call"

    def test_returns_put_from_attribute(self) -> None:
        """Returns normalized put from option_type attribute."""
        option = MagicMock()
        option.option_type = "Put"

        result = resolve_option_type(option)

        assert result == "put"

    def test_defaults_to_call_when_no_attribute(self) -> None:
        """Defaults to 'call' when no option_type attribute."""
        option = MagicMock(spec=[])

        result = resolve_option_type(option)

        assert result == "call"

    def test_raises_for_invalid_option_type(self) -> None:
        """Raises OptionDataConversionError for invalid option type."""
        option = MagicMock()
        option.option_type = "straddle"

        with pytest.raises(OptionDataConversionError) as exc_info:
            resolve_option_type(option)

        assert "Unsupported option type" in str(exc_info.value)


class TestExtractPrices:
    """Tests for extract_prices function."""

    def test_extracts_from_best_bid_ask(self) -> None:
        """Extracts prices from best_bid and best_ask."""
        option = MagicMock()
        option.best_bid = 0.10
        option.best_ask = 0.15

        bid, ask = extract_prices(option)

        assert bid == 0.10
        assert ask == 0.15

    def test_extracts_from_bid_ask_price(self) -> None:
        """Extracts prices from bid_price and ask_price."""
        option = MagicMock(spec=["bid_price", "ask_price"])
        option.bid_price = 0.20
        option.ask_price = 0.25

        bid, ask = extract_prices(option)

        assert bid == 0.20
        assert ask == 0.25

    def test_raises_when_no_price_fields(self) -> None:
        """Raises when no bid/ask price fields."""
        option = MagicMock(spec=[])

        with pytest.raises(OptionDataConversionError) as exc_info:
            extract_prices(option)

        assert "bid/ask price" in str(exc_info.value)

    def test_raises_when_prices_not_numeric(self) -> None:
        """Raises when prices are not numeric."""
        option = MagicMock()
        option.best_bid = "high"
        option.best_ask = "low"

        with pytest.raises(OptionDataConversionError) as exc_info:
            extract_prices(option)

        assert "numeric" in str(exc_info.value)

    def test_raises_when_bid_negative(self) -> None:
        """Raises when bid is negative."""
        option = MagicMock()
        option.best_bid = -0.10
        option.best_ask = 0.15

        with pytest.raises(OptionDataConversionError) as exc_info:
            extract_prices(option)

        assert "non-negative" in str(exc_info.value)

    def test_raises_when_ask_less_than_bid(self) -> None:
        """Raises when ask is less than bid."""
        option = MagicMock()
        option.best_bid = 0.20
        option.best_ask = 0.10

        with pytest.raises(OptionDataConversionError) as exc_info:
            extract_prices(option)

        assert "must be >=" in str(exc_info.value)

    def test_allows_equal_bid_ask(self) -> None:
        """Allows equal bid and ask prices."""
        option = MagicMock()
        option.best_bid = 0.15
        option.best_ask = 0.15

        bid, ask = extract_prices(option)

        assert bid == 0.15
        assert ask == 0.15


class TestExtractSizes:
    """Tests for extract_sizes function."""

    def test_extracts_from_best_bid_ask_size(self) -> None:
        """Extracts sizes from best_bid_size and best_ask_size."""
        option = MagicMock()
        option.best_bid_size = DEFAULT_TEST_CONVERSION_BID_SIZE
        option.best_ask_size = DEFAULT_TEST_CONVERSION_ASK_SIZE

        bid, ask = extract_sizes(option)

        assert bid == DEFAULT_TEST_CONVERSION_BID_SIZE
        assert ask == DEFAULT_TEST_CONVERSION_ASK_SIZE

    def test_extracts_from_bid_ask_size(self) -> None:
        """Extracts sizes from bid_size and ask_size."""
        option = MagicMock(spec=["bid_size", "ask_size"])
        option.bid_size = DEFAULT_TEST_CONVERSION_ALT_BID_SIZE
        option.ask_size = DEFAULT_TEST_CONVERSION_ALT_ASK_SIZE

        bid, ask = extract_sizes(option)

        assert bid == DEFAULT_TEST_CONVERSION_ALT_BID_SIZE
        assert ask == DEFAULT_TEST_CONVERSION_ALT_ASK_SIZE

    def test_raises_when_no_size_fields(self) -> None:
        """Raises when no bid/ask size fields."""
        option = MagicMock(spec=[])

        with pytest.raises(OptionDataConversionError) as exc_info:
            extract_sizes(option)

        assert "sizes" in str(exc_info.value)

    def test_raises_when_sizes_not_numeric(self) -> None:
        """Raises when sizes are not numeric."""
        option = MagicMock()
        option.best_bid_size = "many"
        option.best_ask_size = "few"

        with pytest.raises(OptionDataConversionError) as exc_info:
            extract_sizes(option)

        assert "numeric" in str(exc_info.value)

    def test_raises_when_bid_size_not_positive(self) -> None:
        """Raises when bid size is not positive."""
        option = MagicMock()
        option.best_bid_size = 0
        option.best_ask_size = DEFAULT_TEST_CONVERSION_ASK_SIZE

        with pytest.raises(OptionDataConversionError) as exc_info:
            extract_sizes(option)

        assert "positive" in str(exc_info.value)

    def test_raises_when_ask_size_negative(self) -> None:
        """Raises when ask size is negative."""
        option = MagicMock()
        option.best_bid_size = DEFAULT_TEST_CONVERSION_BID_SIZE
        option.best_ask_size = -50

        with pytest.raises(OptionDataConversionError) as exc_info:
            extract_sizes(option)

        assert "positive" in str(exc_info.value)


class TestResolveTimestamp:
    """Tests for resolve_timestamp function."""

    def test_returns_datetime_timestamp_as_utc(self) -> None:
        """Returns datetime timestamp converted to UTC."""
        option = MagicMock()
        option.timestamp = datetime(2024, 1, 25, 12, 0, 0, tzinfo=timezone.utc)

        result = resolve_timestamp(option)

        assert result == datetime(2024, 1, 25, 12, 0, 0, tzinfo=timezone.utc)

    def test_converts_epoch_timestamp(self) -> None:
        """Converts epoch timestamp to datetime."""
        option = MagicMock()
        option.timestamp = 1706184000  # 2024-01-25 12:00:00 UTC

        result = resolve_timestamp(option)

        assert result.year == 2024
        assert result.tzinfo == timezone.utc

    def test_raises_when_timestamp_invalid(self) -> None:
        """Raises when timestamp is invalid."""
        option = MagicMock()
        option.timestamp = "not-a-timestamp"

        with pytest.raises(OptionDataConversionError) as exc_info:
            resolve_timestamp(option)

        assert "datetime or epoch" in str(exc_info.value)


class TestMicroPriceConversionHelpers:
    """Tests for MicroPriceConversionHelpers class."""

    def test_has_all_static_methods(self) -> None:
        """Has all conversion functions as static methods."""
        assert hasattr(MicroPriceConversionHelpers, "resolve_instrument_name")
        assert hasattr(MicroPriceConversionHelpers, "determine_underlying")
        assert hasattr(MicroPriceConversionHelpers, "determine_expiry")
        assert hasattr(MicroPriceConversionHelpers, "resolve_option_type")
        assert hasattr(MicroPriceConversionHelpers, "extract_prices")
        assert hasattr(MicroPriceConversionHelpers, "extract_sizes")
        assert hasattr(MicroPriceConversionHelpers, "resolve_timestamp")

    def test_static_methods_are_callable(self) -> None:
        """Static methods are callable."""
        option = MagicMock()
        option.instrument_name = "BTC-25JAN24-50000-C"

        result = MicroPriceConversionHelpers.resolve_instrument_name(option)

        assert result == "BTC-25JAN24-50000-C"
