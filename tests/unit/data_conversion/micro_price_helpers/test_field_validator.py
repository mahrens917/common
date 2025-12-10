"""Tests for field validator module."""

from unittest.mock import MagicMock

import pytest

from common.data_conversion.micro_price_helpers.field_validator import FieldValidator

DEFAULT_TEST_BID_SIZE = 100.0
DEFAULT_TEST_ASK_SIZE = 150.0


class TestFieldValidatorValidateRequiredFields:
    """Tests for FieldValidator.validate_required_fields."""

    def test_passes_when_all_fields_present(self) -> None:
        """Passes when all required fields are present."""
        instrument = MagicMock()
        instrument.best_bid = 0.5
        instrument.best_ask = 0.55
        instrument.strike = 50000
        instrument.option_type = "call"
        instrument.expiry = 1705320000
        instrument.symbol = "BTC-C-50000"

        FieldValidator.validate_required_fields(instrument)

    def test_raises_when_best_bid_missing(self) -> None:
        """Raises ValueError when best_bid is missing."""
        instrument = MagicMock()
        instrument.best_bid = None
        instrument.best_ask = 0.55
        instrument.strike = 50000
        instrument.option_type = "call"
        instrument.expiry = 1705320000
        instrument.symbol = "BTC-C-50000"

        with pytest.raises(ValueError) as exc_info:
            FieldValidator.validate_required_fields(instrument)

        assert "best_bid" in str(exc_info.value)

    def test_raises_when_multiple_fields_missing(self) -> None:
        """Raises ValueError listing multiple missing fields."""
        instrument = MagicMock()
        instrument.best_bid = None
        instrument.best_ask = None
        instrument.strike = 50000
        instrument.option_type = "call"
        instrument.expiry = 1705320000
        instrument.symbol = "BTC-C-50000"

        with pytest.raises(ValueError) as exc_info:
            FieldValidator.validate_required_fields(instrument)

        error_msg = str(exc_info.value)
        assert "best_bid" in error_msg
        assert "best_ask" in error_msg

    def test_includes_symbol_in_error_message(self) -> None:
        """Includes symbol in error message."""
        instrument = MagicMock()
        instrument.best_bid = None
        instrument.best_ask = 0.55
        instrument.strike = 50000
        instrument.option_type = "call"
        instrument.expiry = 1705320000
        instrument.symbol = "TEST-SYMBOL"

        with pytest.raises(ValueError) as exc_info:
            FieldValidator.validate_required_fields(instrument)

        assert "TEST-SYMBOL" in str(exc_info.value)


class TestFieldValidatorExtractPricesAndSizes:
    """Tests for FieldValidator.extract_prices_and_sizes."""

    def test_returns_prices_and_sizes(self) -> None:
        """Returns bid price, ask price, bid size, ask size."""
        instrument = MagicMock()
        instrument.best_bid = 0.5
        instrument.best_ask = 0.55
        instrument.best_bid_size = DEFAULT_TEST_BID_SIZE
        instrument.best_ask_size = DEFAULT_TEST_ASK_SIZE

        bid_price, ask_price, bid_size, ask_size = FieldValidator.extract_prices_and_sizes(
            instrument
        )

        assert bid_price == 0.5
        assert ask_price == 0.55
        assert bid_size == DEFAULT_TEST_BID_SIZE
        assert ask_size == DEFAULT_TEST_ASK_SIZE

    def test_converts_to_float(self) -> None:
        """Converts values to float."""
        instrument = MagicMock()
        instrument.best_bid = "0.5"
        instrument.best_ask = "0.55"
        instrument.best_bid_size = "100"
        instrument.best_ask_size = "150"

        bid_price, ask_price, bid_size, ask_size = FieldValidator.extract_prices_and_sizes(
            instrument
        )

        assert isinstance(bid_price, float)
        assert isinstance(ask_price, float)
        assert isinstance(bid_size, float)
        assert isinstance(ask_size, float)

    def test_raises_when_bid_size_missing(self) -> None:
        """Raises ValueError when best_bid_size is missing."""
        instrument = MagicMock()
        instrument.best_bid = 0.5
        instrument.best_ask = 0.55
        instrument.best_bid_size = None
        instrument.best_ask_size = DEFAULT_TEST_ASK_SIZE
        instrument.symbol = "TEST"

        with pytest.raises(ValueError) as exc_info:
            FieldValidator.extract_prices_and_sizes(instrument)

        error_msg = str(exc_info.value)
        assert "best_bid_size" in error_msg
        assert "FAIL-FAST" in error_msg

    def test_raises_when_ask_size_missing(self) -> None:
        """Raises ValueError when best_ask_size is missing."""
        instrument = MagicMock()
        instrument.best_bid = 0.5
        instrument.best_ask = 0.55
        instrument.best_bid_size = DEFAULT_TEST_BID_SIZE
        instrument.best_ask_size = None
        instrument.symbol = "TEST"

        with pytest.raises(ValueError) as exc_info:
            FieldValidator.extract_prices_and_sizes(instrument)

        error_msg = str(exc_info.value)
        assert "best_ask_size" in error_msg
        assert "FAIL-FAST" in error_msg
