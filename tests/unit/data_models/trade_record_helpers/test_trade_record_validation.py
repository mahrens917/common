"""Tests for trade_record_validation module."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.common.data_models.trade_record import TradeSide
from src.common.data_models.trade_record_helpers.trade_record_validation import (
    ERR_INVALID_TRADE_AMOUNT,
    ERR_MISSING_REQUIRED_FIELD,
    validate_and_normalize_category,
    validate_basic_fields,
    validate_cost_calculation,
    validate_quantity_and_price,
    validate_settlement_data,
    validate_trade_metadata,
    validate_trade_record,
    validate_trade_side,
    validate_weather_station,
)
from src.common.exceptions import ValidationError
from src.common.redis_schema.markets import KalshiMarketCategory


class TestValidateBasicFields:
    """Tests for validate_basic_fields function."""

    def test_passes_with_valid_fields(self) -> None:
        """Passes with valid basic fields."""
        trade = MagicMock()
        trade.order_id = "order123"
        trade.market_ticker = "WEATHER-HIGH"
        trade.trade_timestamp = datetime.now()

        # Should not raise
        validate_basic_fields(trade)

    def test_raises_on_missing_order_id(self) -> None:
        """Raises ValueError on missing order_id."""
        trade = MagicMock()
        trade.order_id = ""
        trade.market_ticker = "WEATHER-HIGH"
        trade.trade_timestamp = datetime.now()

        with pytest.raises(ValueError) as exc_info:
            validate_basic_fields(trade)

        assert "Order ID" in str(exc_info.value)

    def test_raises_on_none_order_id(self) -> None:
        """Raises ValueError on None order_id."""
        trade = MagicMock()
        trade.order_id = None
        trade.market_ticker = "WEATHER-HIGH"
        trade.trade_timestamp = datetime.now()

        with pytest.raises(ValueError):
            validate_basic_fields(trade)

    def test_raises_on_missing_market_ticker(self) -> None:
        """Raises ValueError on missing market_ticker."""
        trade = MagicMock()
        trade.order_id = "order123"
        trade.market_ticker = ""
        trade.trade_timestamp = datetime.now()

        with pytest.raises(ValueError) as exc_info:
            validate_basic_fields(trade)

        assert "ticker" in str(exc_info.value)

    def test_raises_on_invalid_timestamp_type(self) -> None:
        """Raises TypeError on invalid timestamp type."""
        trade = MagicMock()
        trade.order_id = "order123"
        trade.market_ticker = "WEATHER-HIGH"
        trade.trade_timestamp = "2024-01-01"  # String instead of datetime

        with pytest.raises(TypeError) as exc_info:
            validate_basic_fields(trade)

        assert "datetime" in str(exc_info.value)


class TestValidateTradeSide:
    """Tests for validate_trade_side function."""

    def test_passes_with_valid_trade_side(self) -> None:
        """Passes with valid TradeSide enum."""
        validate_trade_side(TradeSide.YES)
        validate_trade_side(TradeSide.NO)

    def test_raises_on_string_trade_side(self) -> None:
        """Raises TypeError on string trade side."""
        with pytest.raises(TypeError) as exc_info:
            validate_trade_side("buy")

        assert "TradeSide enum" in str(exc_info.value)

    def test_raises_on_int_trade_side(self) -> None:
        """Raises TypeError on integer trade side."""
        with pytest.raises(TypeError):
            validate_trade_side(1)


class TestValidateQuantityAndPrice:
    """Tests for validate_quantity_and_price function."""

    def test_passes_with_valid_values(self) -> None:
        """Passes with valid quantity, price, and fee."""
        validate_quantity_and_price(10, 50, 5)
        validate_quantity_and_price(1, 1, 0)
        validate_quantity_and_price(1000, 99, 100)

    def test_raises_on_zero_quantity(self) -> None:
        """Raises ValueError on zero quantity."""
        with pytest.raises(ValueError) as exc_info:
            validate_quantity_and_price(0, 50, 5)

        assert "Quantity" in str(exc_info.value)

    def test_raises_on_negative_quantity(self) -> None:
        """Raises ValueError on negative quantity."""
        with pytest.raises(ValueError):
            validate_quantity_and_price(-1, 50, 5)

    def test_raises_on_zero_price(self) -> None:
        """Raises ValueError on zero price."""
        with pytest.raises(ValueError) as exc_info:
            validate_quantity_and_price(10, 0, 5)

        assert "Price" in str(exc_info.value)

    def test_raises_on_price_over_99(self) -> None:
        """Raises ValueError on price over 99."""
        with pytest.raises(ValueError):
            validate_quantity_and_price(10, 100, 5)

    def test_raises_on_negative_fee(self) -> None:
        """Raises ValueError on negative fee."""
        with pytest.raises(ValueError) as exc_info:
            validate_quantity_and_price(10, 50, -1)

        assert "Fee" in str(exc_info.value)


class TestValidateCostCalculation:
    """Tests for validate_cost_calculation function."""

    def test_passes_with_correct_cost(self) -> None:
        """Passes when cost = (price * quantity) + fees."""
        validate_cost_calculation(50, 10, 5, 505)
        validate_cost_calculation(99, 1, 0, 99)
        validate_cost_calculation(25, 100, 50, 2550)

    def test_raises_on_incorrect_cost(self) -> None:
        """Raises ValueError when cost doesn't match calculation."""
        with pytest.raises(ValueError) as exc_info:
            validate_cost_calculation(50, 10, 5, 500)  # Should be 505

        assert "Cost mismatch" in str(exc_info.value)
        assert "505" in str(exc_info.value)
        assert "500" in str(exc_info.value)


class TestValidateAndNormalizeCategory:
    """Tests for validate_and_normalize_category function."""

    def test_passes_with_valid_category_string(self) -> None:
        """Passes with valid category string."""
        result = validate_and_normalize_category("weather")
        assert result == "weather"

    def test_normalizes_uppercase_category(self) -> None:
        """Normalizes uppercase category to lowercase."""
        result = validate_and_normalize_category("WEATHER")
        assert result == "weather"

    def test_passes_with_category_enum(self) -> None:
        """Passes with KalshiMarketCategory enum."""
        result = validate_and_normalize_category(KalshiMarketCategory.WEATHER)
        assert result == "weather"

    def test_raises_on_empty_category(self) -> None:
        """Raises ValueError on empty category."""
        with pytest.raises(ValueError) as exc_info:
            validate_and_normalize_category("")

        assert "must be specified" in str(exc_info.value)

    def test_raises_on_invalid_category(self) -> None:
        """Raises ValueError on invalid category."""
        with pytest.raises(ValueError) as exc_info:
            validate_and_normalize_category("invalid_category")

        assert "Unsupported market category" in str(exc_info.value)


class TestValidateWeatherStation:
    """Tests for validate_weather_station function."""

    def test_passes_with_valid_weather_station(self) -> None:
        """Passes with valid 4-letter station code."""
        result = validate_weather_station("KJFK", "weather")
        assert result == "KJFK"

    def test_normalizes_lowercase_station(self) -> None:
        """Normalizes lowercase station code to uppercase."""
        result = validate_weather_station("kjfk", "weather")
        assert result == "KJFK"

    def test_allows_2_letter_station(self) -> None:
        """Allows 2-letter station codes."""
        result = validate_weather_station("JF", "weather")
        assert result == "JF"

    def test_allows_3_letter_station(self) -> None:
        """Allows 3-letter station codes."""
        result = validate_weather_station("JFK", "weather")
        assert result == "JFK"

    def test_raises_on_missing_station_for_weather(self) -> None:
        """Raises ValueError when station missing for weather trade."""
        with pytest.raises(ValueError) as exc_info:
            validate_weather_station(None, "weather")

        assert "must be specified" in str(exc_info.value)

    def test_raises_on_empty_station_for_weather(self) -> None:
        """Raises ValueError when station empty for weather trade."""
        with pytest.raises(ValueError):
            validate_weather_station("", "weather")

    def test_raises_on_invalid_station_length(self) -> None:
        """Raises ValidationError on invalid station length."""
        with pytest.raises(ValidationError) as exc_info:
            validate_weather_station("KJFKX", "weather")  # 5 letters

        assert "2-4 letter" in str(exc_info.value)

    def test_raises_on_single_letter_station(self) -> None:
        """Raises ValidationError on single letter station."""
        with pytest.raises(ValidationError):
            validate_weather_station("K", "weather")

    def test_returns_station_unchanged_for_non_weather(self) -> None:
        """Returns station unchanged for non-weather category."""
        result = validate_weather_station("INVALID", "crypto")
        assert result == "INVALID"

    def test_returns_none_for_non_weather_without_station(self) -> None:
        """Returns None for non-weather category without station."""
        result = validate_weather_station(None, "crypto")
        assert result is None


class TestValidateTradeMetadata:
    """Tests for validate_trade_metadata function."""

    def test_passes_with_valid_metadata(self) -> None:
        """Passes with valid trade rule and reason."""
        validate_trade_metadata("rule1", "This is a descriptive trade reason")

    def test_raises_on_missing_trade_rule(self) -> None:
        """Raises ValueError on missing trade rule."""
        with pytest.raises(ValueError) as exc_info:
            validate_trade_metadata("", "Valid reason here")

        assert "Trade rule" in str(exc_info.value)

    def test_raises_on_missing_trade_reason(self) -> None:
        """Raises ValueError on missing trade reason."""
        with pytest.raises(ValueError) as exc_info:
            validate_trade_metadata("rule1", "")

        assert "Trade reason" in str(exc_info.value)

    def test_raises_on_short_trade_reason(self) -> None:
        """Raises ValueError on trade reason less than 10 chars."""
        with pytest.raises(ValueError) as exc_info:
            validate_trade_metadata("rule1", "short")

        assert "descriptive" in str(exc_info.value)


class TestValidateSettlementData:
    """Tests for validate_settlement_data function."""

    def test_passes_with_valid_settlement_data(self) -> None:
        """Passes with valid settlement price and time."""
        validate_settlement_data(50, datetime.now())
        validate_settlement_data(0, datetime.now())
        validate_settlement_data(100, datetime.now())

    def test_passes_with_none_values(self) -> None:
        """Passes with None settlement data."""
        validate_settlement_data(None, None)

    def test_raises_on_negative_settlement_price(self) -> None:
        """Raises ValueError on negative settlement price."""
        with pytest.raises(ValueError) as exc_info:
            validate_settlement_data(-1, None)

        assert "Settlement price" in str(exc_info.value)

    def test_raises_on_settlement_price_over_100(self) -> None:
        """Raises ValueError on settlement price over 100."""
        with pytest.raises(ValueError):
            validate_settlement_data(101, None)

    def test_raises_on_invalid_settlement_time_type(self) -> None:
        """Raises ValueError on invalid settlement time type."""
        with pytest.raises(ValueError) as exc_info:
            validate_settlement_data(None, "2024-01-01")

        assert "datetime" in str(exc_info.value)


class TestValidateTradeRecord:
    """Tests for validate_trade_record function."""

    def test_validates_all_fields(self) -> None:
        """Validates all fields in trade record."""
        trade = MagicMock()
        trade.order_id = "order123"
        trade.market_ticker = "WEATHER-HIGH"
        trade.trade_timestamp = datetime.now()
        trade.trade_side = TradeSide.YES
        trade.quantity = 10
        trade.price_cents = 50
        trade.fee_cents = 5
        trade.cost_cents = 505
        trade.market_category = "weather"
        trade.weather_station = "KJFK"
        trade.trade_rule = "rule1"
        trade.trade_reason = "This is a valid trade reason"
        trade.settlement_price_cents = None
        trade.settlement_time = None

        # Should not raise
        validate_trade_record(trade)

        # Check category and station were normalized
        assert trade.market_category == "weather"
        assert trade.weather_station == "KJFK"

    def test_normalizes_category_and_station(self) -> None:
        """Normalizes category and station during validation."""
        trade = MagicMock()
        trade.order_id = "order123"
        trade.market_ticker = "WEATHER-HIGH"
        trade.trade_timestamp = datetime.now()
        trade.trade_side = TradeSide.YES
        trade.quantity = 10
        trade.price_cents = 50
        trade.fee_cents = 5
        trade.cost_cents = 505
        trade.market_category = "WEATHER"
        trade.weather_station = "kjfk"
        trade.trade_rule = "rule1"
        trade.trade_reason = "This is a valid trade reason"
        trade.settlement_price_cents = None
        trade.settlement_time = None

        validate_trade_record(trade)

        assert trade.market_category == "weather"
        assert trade.weather_station == "KJFK"


class TestErrorMessages:
    """Tests for error message constants."""

    def test_error_message_constants_exist(self) -> None:
        """Error message constants are defined."""
        assert ERR_MISSING_REQUIRED_FIELD
        assert "{field}" in ERR_MISSING_REQUIRED_FIELD

        assert ERR_INVALID_TRADE_AMOUNT
        assert "{value}" in ERR_INVALID_TRADE_AMOUNT
