"""Tests for market_validators module."""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from common.validation_helpers.exceptions import ValidationError
from common.validation_helpers.market_validators import MarketValidators

# Test constants for data_guard compliance
TEST_STRIKE_100 = 100.0
TEST_STRIKE_200 = 200.0
TEST_STRIKE_150 = 150.0
TEST_STRIKE_50 = 50.0
TEST_STRIKE_400 = 400.0
TEST_STRIKE_ZERO = 0
TEST_STRIKE_NEGATIVE_10 = -10
TEST_STRIKE_NEGATIVE_50 = -50.0
TEST_BID_40 = 40.0
TEST_ASK_50 = 50.0
TEST_VOLUME_100 = 100
TEST_VOLUME_50 = 50
TEST_VOLUME_ZERO = 0
TEST_VOLUME_NEGATIVE_1 = -1
TEST_INSTRUMENT_NAME_BTC = "BTC option"
TEST_STRING_VOLUME_100 = "100"
TEST_STRING_OPEN_INTEREST_50 = "50"


@dataclass
class MockOption:
    """Mock option for testing."""

    strike: float | None


class TestDeriveStrikePriceBoundsFromMarketData:
    """Tests for derive_strike_price_bounds_from_market_data method."""

    def test_derives_bounds_from_options(self) -> None:
        """Test derives bounds from options data."""
        options = [
            MockOption(strike=TEST_STRIKE_100),
            MockOption(strike=TEST_STRIKE_200),
            MockOption(strike=TEST_STRIKE_150),
        ]

        min_strike, max_strike = MarketValidators.derive_strike_price_bounds_from_market_data(options)

        assert min_strike == TEST_STRIKE_50
        assert max_strike == TEST_STRIKE_400

    def test_single_option(self) -> None:
        """Test derives bounds from single option."""
        options = [MockOption(strike=TEST_STRIKE_100)]

        min_strike, max_strike = MarketValidators.derive_strike_price_bounds_from_market_data(options)

        assert min_strike == TEST_STRIKE_50
        assert max_strike == TEST_STRIKE_200

    def test_empty_options_raises(self) -> None:
        """Test empty options list raises error."""
        with pytest.raises(ValidationError, match="No options data provided"):
            MarketValidators.derive_strike_price_bounds_from_market_data([])

    def test_none_options_raises(self) -> None:
        """Test None options raises error."""
        with pytest.raises(ValidationError, match="No options data provided"):
            MarketValidators.derive_strike_price_bounds_from_market_data(None)

    def test_no_valid_strikes_raises(self) -> None:
        """Test no valid strikes raises error."""
        options = [
            MockOption(strike=None),
            MockOption(strike=TEST_STRIKE_ZERO),
            MockOption(strike=TEST_STRIKE_NEGATIVE_10),
        ]

        with pytest.raises(ValidationError, match="No valid strike prices"):
            MarketValidators.derive_strike_price_bounds_from_market_data(options)

    def test_skips_none_strikes(self) -> None:
        """Test skips options with None strikes."""
        options = [
            MockOption(strike=TEST_STRIKE_100),
            MockOption(strike=None),
            MockOption(strike=TEST_STRIKE_200),
        ]

        min_strike, max_strike = MarketValidators.derive_strike_price_bounds_from_market_data(options)

        assert min_strike == TEST_STRIKE_50
        assert max_strike == TEST_STRIKE_400

    def test_skips_zero_and_negative_strikes(self) -> None:
        """Test skips options with zero or negative strikes."""
        options = [
            MockOption(strike=TEST_STRIKE_100),
            MockOption(strike=TEST_STRIKE_ZERO),
            MockOption(strike=TEST_STRIKE_NEGATIVE_50),
        ]

        min_strike, max_strike = MarketValidators.derive_strike_price_bounds_from_market_data(options)

        assert min_strike == TEST_STRIKE_50
        assert max_strike == TEST_STRIKE_200


class TestValidateBidAskRelationship:
    """Tests for validate_bid_ask_relationship method."""

    def test_valid_bid_ask(self) -> None:
        """Test valid bid <= ask passes."""
        assert MarketValidators.validate_bid_ask_relationship(TEST_BID_40, TEST_ASK_50) is True

    def test_bid_equals_ask(self) -> None:
        """Test bid == ask passes."""
        assert MarketValidators.validate_bid_ask_relationship(TEST_ASK_50, TEST_ASK_50) is True

    def test_zero_bid_and_ask(self) -> None:
        """Test zero bid and ask passes."""
        assert MarketValidators.validate_bid_ask_relationship(TEST_VOLUME_ZERO, TEST_VOLUME_ZERO) is True

    def test_with_instrument_name(self) -> None:
        """Test custom instrument name is used."""
        assert MarketValidators.validate_bid_ask_relationship(TEST_BID_40, TEST_ASK_50, TEST_INSTRUMENT_NAME_BTC) is True


class TestValidateVolumeAndOpenInterest:
    """Tests for validate_volume_and_open_interest method."""

    def test_valid_values(self) -> None:
        """Test valid volume and open interest passes."""
        assert MarketValidators.validate_volume_and_open_interest(TEST_VOLUME_100, TEST_VOLUME_50) is True

    def test_zero_values(self) -> None:
        """Test zero values are valid."""
        assert MarketValidators.validate_volume_and_open_interest(TEST_VOLUME_ZERO, TEST_VOLUME_ZERO) is True

    def test_negative_volume_raises(self) -> None:
        """Test negative volume raises error."""
        with pytest.raises(ValidationError, match="Volume.*cannot be negative"):
            MarketValidators.validate_volume_and_open_interest(TEST_VOLUME_NEGATIVE_1, TEST_VOLUME_50)

    def test_negative_open_interest_raises(self) -> None:
        """Test negative open interest raises error."""
        with pytest.raises(ValidationError, match="Open interest.*cannot be negative"):
            MarketValidators.validate_volume_and_open_interest(TEST_VOLUME_100, TEST_VOLUME_NEGATIVE_1)

    def test_non_integer_volume_raises(self) -> None:
        """Test non-integer volume raises error."""
        with pytest.raises(ValidationError, match="Volume must be integer"):
            MarketValidators.validate_volume_and_open_interest(TEST_STRING_VOLUME_100, TEST_VOLUME_50)

    def test_non_integer_open_interest_raises(self) -> None:
        """Test non-integer open interest raises error."""
        with pytest.raises(ValidationError, match="Open interest must be integer"):
            MarketValidators.validate_volume_and_open_interest(TEST_VOLUME_100, TEST_STRING_OPEN_INTEREST_50)
