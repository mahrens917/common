"""Tests for market_validators module."""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from common.validation_helpers.exceptions import ValidationError
from common.validation_helpers.market_validators import MarketValidators


@dataclass
class MockOption:
    """Mock option for testing."""

    strike: float | None


class TestDeriveStrikePriceBoundsFromMarketData:
    """Tests for derive_strike_price_bounds_from_market_data method."""

    def test_derives_bounds_from_options(self) -> None:
        """Test derives bounds from options data."""
        options = [
            MockOption(strike=100.0),
            MockOption(strike=200.0),
            MockOption(strike=150.0),
        ]

        min_strike, max_strike = MarketValidators.derive_strike_price_bounds_from_market_data(options)

        assert min_strike == 50.0
        assert max_strike == 400.0

    def test_single_option(self) -> None:
        """Test derives bounds from single option."""
        options = [MockOption(strike=100.0)]

        min_strike, max_strike = MarketValidators.derive_strike_price_bounds_from_market_data(options)

        assert min_strike == 50.0
        assert max_strike == 200.0

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
            MockOption(strike=0),
            MockOption(strike=-10),
        ]

        with pytest.raises(ValidationError, match="No valid strike prices"):
            MarketValidators.derive_strike_price_bounds_from_market_data(options)

    def test_skips_none_strikes(self) -> None:
        """Test skips options with None strikes."""
        options = [
            MockOption(strike=100.0),
            MockOption(strike=None),
            MockOption(strike=200.0),
        ]

        min_strike, max_strike = MarketValidators.derive_strike_price_bounds_from_market_data(options)

        assert min_strike == 50.0
        assert max_strike == 400.0

    def test_skips_zero_and_negative_strikes(self) -> None:
        """Test skips options with zero or negative strikes."""
        options = [
            MockOption(strike=100.0),
            MockOption(strike=0),
            MockOption(strike=-50.0),
        ]

        min_strike, max_strike = MarketValidators.derive_strike_price_bounds_from_market_data(options)

        assert min_strike == 50.0
        assert max_strike == 200.0


class TestValidateBidAskRelationship:
    """Tests for validate_bid_ask_relationship method."""

    def test_valid_bid_ask(self) -> None:
        """Test valid bid <= ask passes."""
        assert MarketValidators.validate_bid_ask_relationship(40.0, 50.0) is True

    def test_bid_equals_ask(self) -> None:
        """Test bid == ask passes."""
        assert MarketValidators.validate_bid_ask_relationship(50.0, 50.0) is True

    def test_zero_bid_and_ask(self) -> None:
        """Test zero bid and ask passes."""
        assert MarketValidators.validate_bid_ask_relationship(0.0, 0.0) is True

    def test_with_instrument_name(self) -> None:
        """Test custom instrument name is used."""
        assert MarketValidators.validate_bid_ask_relationship(40.0, 50.0, "BTC option") is True


class TestValidateVolumeAndOpenInterest:
    """Tests for validate_volume_and_open_interest method."""

    def test_valid_values(self) -> None:
        """Test valid volume and open interest passes."""
        assert MarketValidators.validate_volume_and_open_interest(100, 50) is True

    def test_zero_values(self) -> None:
        """Test zero values are valid."""
        assert MarketValidators.validate_volume_and_open_interest(0, 0) is True

    def test_negative_volume_raises(self) -> None:
        """Test negative volume raises error."""
        with pytest.raises(ValidationError, match="Volume.*cannot be negative"):
            MarketValidators.validate_volume_and_open_interest(-1, 50)

    def test_negative_open_interest_raises(self) -> None:
        """Test negative open interest raises error."""
        with pytest.raises(ValidationError, match="Open interest.*cannot be negative"):
            MarketValidators.validate_volume_and_open_interest(100, -1)

    def test_non_integer_volume_raises(self) -> None:
        """Test non-integer volume raises error."""
        with pytest.raises(ValidationError, match="Volume must be integer"):
            MarketValidators.validate_volume_and_open_interest("100", 50)

    def test_non_integer_open_interest_raises(self) -> None:
        """Test non-integer open interest raises error."""
        with pytest.raises(ValidationError, match="Open interest must be integer"):
            MarketValidators.validate_volume_and_open_interest(100, "50")
