"""Comprehensive unit tests for delta_processor_helpers.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import orjson
import pytest
from redis.exceptions import RedisError

from src.common.redis_protocol.kalshi_store.orderbook_helpers.delta_processor_helpers import (
    apply_delta_to_orderbook,
    determine_side_field_and_price,
    extract_trade_prices,
    update_best_prices,
    validate_delta_message,
)


class TestValidateDeltaMessage:
    """Tests for validate_delta_message function."""

    def test_valid_delta_message_yes_side(self):
        """Test validation of valid yes-side delta message."""
        msg_data = {"side": "yes", "price": 50, "delta": 10}
        is_valid, side, price, delta = validate_delta_message(msg_data)

        assert is_valid is True
        assert side == "yes"
        assert price == 50
        assert delta == 10

    def test_valid_delta_message_no_side(self):
        """Test validation of valid no-side delta message."""
        msg_data = {"side": "no", "price": 45.5, "delta": 5.0}
        is_valid, side, price, delta = validate_delta_message(msg_data)

        assert is_valid is True
        assert side == "no"
        assert price == 45.5
        assert delta == 5.0

    def test_valid_delta_message_uppercase_side(self):
        """Test validation with uppercase side (should be lowercased)."""
        msg_data = {"side": "YES", "price": 60, "delta": 20}
        is_valid, side, price, delta = validate_delta_message(msg_data)

        assert is_valid is True
        assert side == "yes"
        assert price == 60
        assert delta == 20

    def test_invalid_missing_side(self):
        """Test validation passes when side is missing but returns empty string."""
        msg_data = {"price": 50, "delta": 10}
        is_valid, side, price, delta = validate_delta_message(msg_data)

        assert is_valid is True
        assert side == ""
        assert price == 50
        assert delta == 10

    def test_invalid_missing_price(self):
        """Test validation fails when price is missing."""
        msg_data = {"side": "yes", "delta": 10}
        is_valid, side, price, delta = validate_delta_message(msg_data)

        assert is_valid is False
        assert side is None
        assert price is None
        assert delta is None

    def test_invalid_missing_delta(self):
        """Test validation fails when delta is missing."""
        msg_data = {"side": "yes", "price": 50}
        is_valid, side, price, delta = validate_delta_message(msg_data)

        assert is_valid is False
        assert side is None
        assert price is None
        assert delta is None

    def test_invalid_none_side(self):
        """Test validation passes when side is None but returns empty string."""
        msg_data = {"side": None, "price": 50, "delta": 10}
        is_valid, side, price, delta = validate_delta_message(msg_data)

        assert is_valid is True
        assert side == ""
        assert price == 50
        assert delta == 10

    def test_invalid_string_price(self):
        """Test validation fails when price is non-numeric string."""
        msg_data = {"side": "yes", "price": "not_a_number", "delta": 10}
        is_valid, side, price, delta = validate_delta_message(msg_data)

        assert is_valid is False
        assert side is None
        assert price is None
        assert delta is None

    def test_invalid_string_delta(self):
        """Test validation fails when delta is non-numeric string."""
        msg_data = {"side": "yes", "price": 50, "delta": "invalid"}
        is_valid, side, price, delta = validate_delta_message(msg_data)

        assert is_valid is False
        assert side is None
        assert price is None
        assert delta is None

    def test_invalid_list_price(self):
        """Test validation fails when price is a list."""
        msg_data = {"side": "yes", "price": [50], "delta": 10}
        is_valid, side, price, delta = validate_delta_message(msg_data)

        assert is_valid is False
        assert side is None
        assert price is None
        assert delta is None

    def test_invalid_dict_delta(self):
        """Test validation fails when delta is a dict."""
        msg_data = {"side": "yes", "price": 50, "delta": {"value": 10}}
        is_valid, side, price, delta = validate_delta_message(msg_data)

        assert is_valid is False
        assert side is None
        assert price is None
        assert delta is None

    def test_valid_zero_delta(self):
        """Test validation allows zero delta."""
        msg_data = {"side": "yes", "price": 50, "delta": 0}
        is_valid, side, price, delta = validate_delta_message(msg_data)

        assert is_valid is True
        assert side == "yes"
        assert price == 50
        assert delta == 0

    def test_valid_negative_delta(self):
        """Test validation allows negative delta."""
        msg_data = {"side": "yes", "price": 50, "delta": -5}
        is_valid, side, price, delta = validate_delta_message(msg_data)

        assert is_valid is True
        assert side == "yes"
        assert price == 50
        assert delta == -5

    def test_valid_float_values(self):
        """Test validation with float price and delta."""
        msg_data = {"side": "no", "price": 47.25, "delta": 3.5}
        is_valid, side, price, delta = validate_delta_message(msg_data)

        assert is_valid is True
        assert side == "no"
        assert price == 47.25
        assert delta == 3.5


class TestDetermineSideFieldAndPrice:
    """Tests for determine_side_field_and_price function."""

    def test_yes_side_returns_yes_bids(self):
        """Test yes side returns yes_bids field."""
        side_field, price_str = determine_side_field_and_price("yes", 50.0)

        assert side_field == "yes_bids"
        assert price_str == "50.0"

    def test_yes_side_with_decimal_price(self):
        """Test yes side with decimal price."""
        side_field, price_str = determine_side_field_and_price("yes", 47.25)

        assert side_field == "yes_bids"
        assert price_str == "47.25"

    def test_no_side_returns_yes_asks_with_converted_price(self):
        """Test no side returns yes_asks field with price conversion."""
        side_field, price_str = determine_side_field_and_price("no", 40.0)

        assert side_field == "yes_asks"
        assert price_str == "60.0"

    def test_no_side_price_conversion_decimal(self):
        """Test no side price conversion with decimal."""
        side_field, price_str = determine_side_field_and_price("no", 35.5)

        assert side_field == "yes_asks"
        assert price_str == "64.5"

    def test_no_side_price_conversion_edge_case_zero(self):
        """Test no side price conversion with zero."""
        side_field, price_str = determine_side_field_and_price("no", 0.0)

        assert side_field == "yes_asks"
        assert price_str == "100.0"

    def test_no_side_price_conversion_edge_case_hundred(self):
        """Test no side price conversion with 100."""
        side_field, price_str = determine_side_field_and_price("no", 100.0)

        assert side_field == "yes_asks"
        assert price_str == "0.0"

    def test_unknown_side_returns_none(self):
        """Test unknown side returns None tuple."""
        side_field, price_str = determine_side_field_and_price("maybe", 50.0)

        assert side_field is None
        assert price_str is None

    def test_empty_side_returns_none(self):
        """Test empty side returns None tuple."""
        side_field, price_str = determine_side_field_and_price("", 50.0)

        assert side_field is None
        assert price_str is None

    def test_invalid_side_returns_none(self):
        """Test invalid side returns None tuple."""
        side_field, price_str = determine_side_field_and_price("invalid", 50.0)

        assert side_field is None
        assert price_str is None


@pytest.mark.asyncio
class TestApplyDeltaToOrderbook:
    """Tests for apply_delta_to_orderbook function."""

    async def test_apply_delta_to_existing_level(self):
        """Test applying delta to existing price level."""
        redis = AsyncMock()
        side_data = {"50.0": 10, "55.0": 5}
        redis.hget.return_value = orjson.dumps(side_data)

        result = await apply_delta_to_orderbook(
            redis=redis,
            market_key="market:TEST",
            side_field="yes_bids",
            price_str="50.0",
            delta=5.0,
        )

        assert result == {"50.0": 15, "55.0": 5}
        redis.hget.assert_awaited_once_with("market:TEST", "yes_bids")

    async def test_apply_delta_to_new_level(self):
        """Test applying delta to new price level."""
        redis = AsyncMock()
        side_data = {"50.0": 10}
        redis.hget.return_value = orjson.dumps(side_data)

        result = await apply_delta_to_orderbook(
            redis=redis,
            market_key="market:TEST",
            side_field="yes_bids",
            price_str="55.0",
            delta=8.0,
        )

        assert result == {"50.0": 10, "55.0": 8}

    async def test_apply_negative_delta_removes_level(self):
        """Test applying negative delta that removes price level."""
        redis = AsyncMock()
        side_data = {"50.0": 10, "55.0": 5}
        redis.hget.return_value = orjson.dumps(side_data)

        result = await apply_delta_to_orderbook(
            redis=redis,
            market_key="market:TEST",
            side_field="yes_bids",
            price_str="55.0",
            delta=-5.0,
        )

        assert result == {"50.0": 10}
        assert "55.0" not in result

    async def test_apply_negative_delta_reduces_level(self):
        """Test applying negative delta that reduces but doesn't remove level."""
        redis = AsyncMock()
        side_data = {"50.0": 10}
        redis.hget.return_value = orjson.dumps(side_data)

        result = await apply_delta_to_orderbook(
            redis=redis,
            market_key="market:TEST",
            side_field="yes_bids",
            price_str="50.0",
            delta=-3.0,
        )

        assert result == {"50.0": 7}

    async def test_apply_delta_to_empty_orderbook(self):
        """Test applying delta to empty orderbook."""
        redis = AsyncMock()
        redis.hget.return_value = orjson.dumps({})

        result = await apply_delta_to_orderbook(
            redis=redis,
            market_key="market:TEST",
            side_field="yes_bids",
            price_str="50.0",
            delta=10.0,
        )

        assert result == {"50.0": 10}

    async def test_apply_delta_with_none_side_json(self):
        """Test applying delta when side JSON is None."""
        redis = AsyncMock()
        redis.hget.return_value = None

        result = await apply_delta_to_orderbook(
            redis=redis,
            market_key="market:TEST",
            side_field="yes_bids",
            price_str="50.0",
            delta=10.0,
        )

        assert result == {"50.0": 10}

    async def test_redis_error_propagates(self):
        """Test that Redis errors are propagated."""
        redis = AsyncMock()
        redis.hget.side_effect = RedisError("Connection lost")

        with pytest.raises(RedisError, match="Connection lost"):
            await apply_delta_to_orderbook(
                redis=redis,
                market_key="market:TEST",
                side_field="yes_bids",
                price_str="50.0",
                delta=10.0,
            )

    async def test_runtime_error_propagates(self):
        """Test that RuntimeError is propagated."""
        redis = AsyncMock()
        redis.hget.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(RuntimeError, match="Unexpected error"):
            await apply_delta_to_orderbook(
                redis=redis,
                market_key="market:TEST",
                side_field="yes_bids",
                price_str="50.0",
                delta=10.0,
            )

    async def test_os_error_propagates(self):
        """Test that OSError is propagated."""
        redis = AsyncMock()
        redis.hget.side_effect = OSError("IO error")

        with pytest.raises(OSError, match="IO error"):
            await apply_delta_to_orderbook(
                redis=redis,
                market_key="market:TEST",
                side_field="yes_bids",
                price_str="50.0",
                delta=10.0,
            )


@pytest.mark.asyncio
class TestUpdateBestPrices:
    """Tests for update_best_prices function."""

    @patch(
        "src.common.redis_protocol.kalshi_store.orderbook_helpers.delta_processor_helpers.extract_best_bid"
    )
    async def test_update_yes_bids_best_prices(self, mock_extract_bid):
        """Test updating best prices for yes_bids."""
        mock_extract_bid.return_value = (95.0, 100)
        redis = AsyncMock()
        side_data = {"95.0": 100, "90.0": 50}
        store_optional_field_func = AsyncMock()

        await update_best_prices(
            redis=redis,
            market_key="market:TEST",
            side_field="yes_bids",
            side_data=side_data,
            store_optional_field_func=store_optional_field_func,
        )

        assert store_optional_field_func.await_count == 2
        store_optional_field_func.assert_any_await(redis, "market:TEST", "yes_bid", 95.0)
        store_optional_field_func.assert_any_await(redis, "market:TEST", "yes_bid_size", 100)

    @patch(
        "src.common.redis_protocol.kalshi_store.orderbook_helpers.delta_processor_helpers.extract_best_ask"
    )
    async def test_update_yes_asks_best_prices(self, mock_extract_ask):
        """Test updating best prices for yes_asks."""
        mock_extract_ask.return_value = (98.0, 75)
        redis = AsyncMock()
        side_data = {"98.0": 75, "100.0": 50}
        store_optional_field_func = AsyncMock()

        await update_best_prices(
            redis=redis,
            market_key="market:TEST",
            side_field="yes_asks",
            side_data=side_data,
            store_optional_field_func=store_optional_field_func,
        )

        assert store_optional_field_func.await_count == 2
        store_optional_field_func.assert_any_await(redis, "market:TEST", "yes_ask", 98.0)
        store_optional_field_func.assert_any_await(redis, "market:TEST", "yes_ask_size", 75)

    @patch(
        "src.common.redis_protocol.kalshi_store.orderbook_helpers.delta_processor_helpers.extract_best_bid"
    )
    async def test_update_yes_bids_with_none_values(self, mock_extract_bid):
        """Test updating yes_bids when extract returns None."""
        mock_extract_bid.return_value = (None, None)
        redis = AsyncMock()
        side_data = {}
        store_optional_field_func = AsyncMock()

        await update_best_prices(
            redis=redis,
            market_key="market:TEST",
            side_field="yes_bids",
            side_data=side_data,
            store_optional_field_func=store_optional_field_func,
        )

        assert store_optional_field_func.await_count == 2
        store_optional_field_func.assert_any_await(redis, "market:TEST", "yes_bid", None)
        store_optional_field_func.assert_any_await(redis, "market:TEST", "yes_bid_size", None)

    @patch(
        "src.common.redis_protocol.kalshi_store.orderbook_helpers.delta_processor_helpers.extract_best_ask"
    )
    async def test_update_yes_asks_with_none_values(self, mock_extract_ask):
        """Test updating yes_asks when extract returns None."""
        mock_extract_ask.return_value = (None, None)
        redis = AsyncMock()
        side_data = {}
        store_optional_field_func = AsyncMock()

        await update_best_prices(
            redis=redis,
            market_key="market:TEST",
            side_field="yes_asks",
            side_data=side_data,
            store_optional_field_func=store_optional_field_func,
        )

        assert store_optional_field_func.await_count == 2
        store_optional_field_func.assert_any_await(redis, "market:TEST", "yes_ask", None)
        store_optional_field_func.assert_any_await(redis, "market:TEST", "yes_ask_size", None)


@pytest.mark.asyncio
class TestExtractTradePrices:
    """Tests for extract_trade_prices function."""

    async def test_extract_both_prices_as_bytes(self):
        """Test extracting both prices when stored as bytes."""
        redis = AsyncMock()
        redis.hget.side_effect = [b"95.0", b"98.0"]

        yes_bid, yes_ask = await extract_trade_prices(redis, "market:TEST")

        assert yes_bid == 95.0
        assert yes_ask == 98.0
        assert redis.hget.await_count == 2

    async def test_extract_both_prices_as_strings(self):
        """Test extracting both prices when stored as strings."""
        redis = AsyncMock()
        redis.hget.side_effect = ["95.5", "97.5"]

        yes_bid, yes_ask = await extract_trade_prices(redis, "market:TEST")

        assert yes_bid == 95.5
        assert yes_ask == 97.5

    async def test_extract_prices_with_none_values(self):
        """Test extracting prices when values are None."""
        redis = AsyncMock()
        redis.hget.side_effect = [None, None]

        yes_bid, yes_ask = await extract_trade_prices(redis, "market:TEST")

        assert yes_bid is None
        assert yes_ask is None

    async def test_extract_prices_with_mixed_none(self):
        """Test extracting prices with one None value."""
        redis = AsyncMock()
        redis.hget.side_effect = [b"95.0", None]

        yes_bid, yes_ask = await extract_trade_prices(redis, "market:TEST")

        assert yes_bid == 95.0
        assert yes_ask is None

    async def test_extract_prices_with_invalid_values(self):
        """Test extracting prices with invalid numeric values."""
        redis = AsyncMock()
        redis.hget.side_effect = [b"invalid", b"98.0"]

        yes_bid, yes_ask = await extract_trade_prices(redis, "market:TEST")

        assert yes_bid is None
        assert yes_ask == 98.0

    async def test_extract_prices_with_empty_strings(self):
        """Test extracting prices with empty strings."""
        redis = AsyncMock()
        redis.hget.side_effect = [b"", b"98.0"]

        yes_bid, yes_ask = await extract_trade_prices(redis, "market:TEST")

        assert yes_bid is None
        assert yes_ask == 98.0

    async def test_extract_prices_integer_values(self):
        """Test extracting prices as integer strings."""
        redis = AsyncMock()
        redis.hget.side_effect = [b"95", b"98"]

        yes_bid, yes_ask = await extract_trade_prices(redis, "market:TEST")

        assert yes_bid == 95.0
        assert yes_ask == 98.0

    async def test_extract_prices_zero_values(self):
        """Test extracting prices with zero values."""
        redis = AsyncMock()
        redis.hget.side_effect = [b"0", b"0"]

        yes_bid, yes_ask = await extract_trade_prices(redis, "market:TEST")

        assert yes_bid == 0.0
        assert yes_ask == 0.0

    async def test_extract_prices_decimal_precision(self):
        """Test extracting prices with high decimal precision."""
        redis = AsyncMock()
        redis.hget.side_effect = [b"95.12345", b"98.67890"]

        yes_bid, yes_ask = await extract_trade_prices(redis, "market:TEST")

        assert yes_bid == pytest.approx(95.12345)
        assert yes_ask == pytest.approx(98.67890)

    async def test_extract_prices_bytearray_values(self):
        """Test extracting prices from bytearray values."""
        redis = AsyncMock()
        redis.hget.side_effect = [bytearray(b"95.0"), bytearray(b"98.0")]

        yes_bid, yes_ask = await extract_trade_prices(redis, "market:TEST")

        assert yes_bid == 95.0
        assert yes_ask == 98.0
