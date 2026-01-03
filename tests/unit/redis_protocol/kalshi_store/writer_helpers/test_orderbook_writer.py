"""Tests for orderbook_writer module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.kalshi_store.writer_helpers.orderbook_writer import (
    OrderbookWriter,
    UserDataWriter,
    _build_trade_base_mapping,
    _maybe_set_field,
    _resolve_fill_price,
)


class TestOrderbookWriter:
    """Tests for OrderbookWriter class."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hset = AsyncMock()
        return redis

    @pytest.fixture
    def writer(self, mock_redis):
        return OrderbookWriter(mock_redis, MagicMock())

    @pytest.mark.asyncio
    async def test_update_trade_tick_success(self, writer, mock_redis):
        msg = {"msg": {"market_ticker": "ABC", "side": "yes", "yes_price": 50, "count": 10, "ts": 1700000000}}
        key_func = MagicMock(return_value="key:ABC")
        map_func = MagicMock(side_effect=lambda x: x)
        str_func = MagicMock(side_effect=lambda x: str(x) if x else None)

        result = await writer.update_trade_tick(msg, key_func, map_func, str_func)

        assert result is True
        mock_redis.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_trade_tick_missing_ticker(self, writer, mock_redis):
        msg = {"msg": {"side": "yes", "yes_price": 50}}
        key_func = MagicMock()
        map_func = MagicMock(side_effect=lambda x: x)
        str_func = MagicMock(side_effect=lambda x: str(x) if x else None)

        result = await writer.update_trade_tick(msg, key_func, map_func, str_func)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_trade_tick_value_error(self, writer, mock_redis):
        msg = {"msg": {"market_ticker": "ABC", "side": "yes"}}
        key_func = MagicMock()
        map_func = MagicMock(side_effect=ValueError("test error"))
        str_func = MagicMock()

        result = await writer.update_trade_tick(msg, key_func, map_func, str_func)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_trade_tick_redis_error(self, writer, mock_redis):
        from redis import RedisError

        msg = {"msg": {"market_ticker": "ABC", "side": "yes", "yes_price": 50, "count": 10, "ts": 1700000000}}
        key_func = MagicMock(return_value="key:ABC")
        map_func = MagicMock(side_effect=lambda x: x)
        str_func = MagicMock(side_effect=lambda x: str(x) if x else None)
        mock_redis.hset = AsyncMock(side_effect=RedisError("connection error"))

        result = await writer.update_trade_tick(msg, key_func, map_func, str_func)

        assert result is False

    def test_extract_price_data_with_yes_price(self, writer):
        msg = {"side": "yes", "yes_price": 50}
        str_func = MagicMock(side_effect=lambda x: str(x) if x else None)

        side, yes, no, raw = writer._extract_price_data(msg, str_func)

        assert side == "yes"
        assert yes == 50
        assert no == 50.0

    def test_extract_price_data_with_no_price(self, writer):
        msg = {"side": "no", "no_price": 40}
        str_func = MagicMock(side_effect=lambda x: str(x) if x else None)

        side, yes, no, raw = writer._extract_price_data(msg, str_func)

        assert side == "no"
        assert yes == 60.0
        assert no == 40

    def test_extract_price_data_with_raw_price_yes_side(self, writer):
        msg = {"side": "yes", "price": 45}
        str_func = MagicMock(side_effect=lambda x: str(x) if x else None)

        side, yes, no, raw = writer._extract_price_data(msg, str_func)

        assert side == "yes"
        assert yes == 45
        assert raw == 45

    def test_extract_price_data_with_raw_price_no_side(self, writer):
        msg = {"side": "no", "price": 45}
        str_func = MagicMock(side_effect=lambda x: str(x) if x else None)

        side, yes, no, raw = writer._extract_price_data(msg, str_func)

        assert side == "no"
        assert yes == 55
        assert raw == 45

    def test_extract_price_data_invalid_yes_price(self, writer):
        msg = {"side": "yes", "yes_price": "invalid"}
        str_func = MagicMock(side_effect=lambda x: str(x) if x else None)

        side, yes, no, raw = writer._extract_price_data(msg, str_func)

        assert side == "yes"
        assert yes == "invalid"
        assert no is None

    def test_derive_yes_price_from_raw_invalid(self):
        result = OrderbookWriter._derive_yes_price_from_raw("invalid", "yes")

        assert result is None

    def test_derive_yes_price_from_raw_unknown_side(self):
        result = OrderbookWriter._derive_yes_price_from_raw(50, "unknown")

        assert result is None

    def test_build_trade_mapping(self, writer):
        msg = {"count": 10, "taker_side": "yes"}

        mapping = writer._build_trade_mapping(msg, "yes", 50, 50, 50)

        assert "last_trade_side" in mapping
        assert "last_trade_yes_price" in mapping
        assert "last_trade_no_price" in mapping


class TestUserDataWriter:
    """Tests for UserDataWriter class."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.hset = AsyncMock()
        redis.lpush = AsyncMock()
        redis.ltrim = AsyncMock()
        return redis

    @pytest.fixture
    def writer(self, mock_redis):
        return UserDataWriter(mock_redis, MagicMock())

    @pytest.mark.asyncio
    async def test_update_user_fill_success_yes_side(self, writer, mock_redis):
        msg = {
            "msg": {
                "ticker": "ABC",
                "trade_id": "123",
                "side": "yes",
                "action": "buy",
                "count": 10,
                "yes_price": 50,
                "ts": 1700000000000,
            }
        }

        result = await writer.update_user_fill(msg)

        assert result is True
        mock_redis.hset.assert_called_once()
        call_args = mock_redis.hset.call_args
        mapping = call_args.kwargs["mapping"]
        assert mapping["price"] == "50"
        mock_redis.lpush.assert_called_once()
        mock_redis.ltrim.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_fill_success_no_side(self, writer, mock_redis):
        msg = {
            "msg": {
                "ticker": "ABC",
                "trade_id": "123",
                "side": "no",
                "action": "buy",
                "count": 10,
                "yes_price": 75,
                "ts": 1700000000000,
            }
        }

        result = await writer.update_user_fill(msg)

        assert result is True
        mock_redis.hset.assert_called_once()
        call_args = mock_redis.hset.call_args
        mapping = call_args.kwargs["mapping"]
        assert mapping["price"] == "25"

    @pytest.mark.asyncio
    async def test_update_user_fill_missing_ticker(self, writer):
        msg = {"msg": {"trade_id": "123", "side": "yes", "yes_price": 50}}

        result = await writer.update_user_fill(msg)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_user_fill_missing_trade_id(self, writer):
        msg = {"msg": {"ticker": "ABC", "side": "yes", "yes_price": 50}}

        result = await writer.update_user_fill(msg)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_user_fill_missing_yes_price(self, writer):
        msg = {"msg": {"ticker": "ABC", "trade_id": "123", "side": "yes"}}

        result = await writer.update_user_fill(msg)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_user_fill_flat_msg(self, writer, mock_redis):
        msg = {
            "ticker": "ABC",
            "trade_id": "123",
            "side": "yes",
            "action": "buy",
            "count": 10,
            "yes_price": 50,
        }

        result = await writer.update_user_fill(msg)

        assert result is True

    @pytest.mark.asyncio
    async def test_update_user_fill_redis_error(self, writer, mock_redis):
        from redis import RedisError

        msg = {"msg": {"ticker": "ABC", "trade_id": "123", "side": "yes", "yes_price": 50}}
        mock_redis.hset = AsyncMock(side_effect=RedisError("connection error"))

        result = await writer.update_user_fill(msg)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_user_order_success(self, writer, mock_redis):
        msg = {
            "msg": {
                "ticker": "ABC",
                "order_id": "456",
                "status": "open",
                "action": "buy",
                "side": "yes",
                "type": "limit",
                "count": 10,
                "remaining_count": 10,
                "price": 50,
                "ts": 1700000000000,
            }
        }

        result = await writer.update_user_order(msg)

        assert result is True
        mock_redis.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_order_missing_ticker(self, writer):
        msg = {"msg": {"order_id": "456", "status": "open"}}

        result = await writer.update_user_order(msg)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_user_order_missing_order_id(self, writer):
        msg = {"msg": {"ticker": "ABC", "status": "open"}}

        result = await writer.update_user_order(msg)

        assert result is False

    @pytest.mark.asyncio
    async def test_update_user_order_flat_msg(self, writer, mock_redis):
        msg = {
            "ticker": "ABC",
            "order_id": "456",
            "status": "open",
        }

        result = await writer.update_user_order(msg)

        assert result is True

    @pytest.mark.asyncio
    async def test_update_user_order_redis_error(self, writer, mock_redis):
        from redis import RedisError

        msg = {"msg": {"ticker": "ABC", "order_id": "456", "status": "open"}}
        mock_redis.hset = AsyncMock(side_effect=RedisError("connection error"))

        result = await writer.update_user_order(msg)

        assert result is False


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_build_trade_base_mapping(self):
        mapping = _build_trade_base_mapping("yes", {"count": 10}, "2023-01-01T00:00:00", 1700000000)

        assert mapping["last_trade_side"] == "yes"
        assert mapping["last_trade_count"] == "10"
        assert mapping["last_trade_timestamp"] == "2023-01-01T00:00:00"

    def test_build_trade_base_mapping_no_timestamp(self):
        mapping = _build_trade_base_mapping("no", {"quantity": 5}, "", None)

        assert mapping["last_trade_side"] == "no"
        assert mapping["last_trade_count"] == "5"
        assert mapping["last_trade_timestamp"] == ""

    def test_build_trade_base_mapping_with_size(self):
        mapping = _build_trade_base_mapping("yes", {"size": 20}, "", "raw_ts")

        assert mapping["last_trade_count"] == "20"
        assert mapping["last_trade_timestamp"] == "raw_ts"

    def test_maybe_set_field_with_value(self):
        mapping = {}
        _maybe_set_field(mapping, "test_field", 42)

        assert mapping["test_field"] == "42"

    def test_maybe_set_field_with_none(self):
        mapping = {}
        _maybe_set_field(mapping, "test_field", None)

        assert "test_field" not in mapping

    def test_resolve_fill_price_yes_side(self):
        data = {"yes_price": 50, "side": "yes"}
        assert _resolve_fill_price(data) == 50

    def test_resolve_fill_price_no_side(self):
        data = {"yes_price": 75, "side": "no"}
        assert _resolve_fill_price(data) == 25

    def test_resolve_fill_price_missing_yes_price(self):
        data = {"side": "yes"}
        with pytest.raises(ValueError, match="Fill missing yes_price field"):
            _resolve_fill_price(data)

    def test_resolve_fill_price_invalid_yes_price(self):
        data = {"yes_price": "invalid", "side": "yes"}
        with pytest.raises(ValueError, match="Invalid yes_price value"):
            _resolve_fill_price(data)

    def test_resolve_fill_price_invalid_side(self):
        data = {"yes_price": 50, "side": "unknown"}
        with pytest.raises(ValueError, match="Invalid fill side"):
            _resolve_fill_price(data)
