"""Tests for trading_toggle_api module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.trading_toggle_api import (
    TRADING_ENABLED_KEY,
    _parse_trading_enabled_value,
    is_trading_enabled,
    set_trading_enabled,
    toggle_trading,
)


class TestIsTradingEnabled:
    """Tests for is_trading_enabled function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.get = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_returns_false_when_none(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)

        result = await is_trading_enabled(mock_redis)

        assert result is False
        mock_redis.get.assert_called_once_with(TRADING_ENABLED_KEY)

    @pytest.mark.asyncio
    async def test_returns_true_when_bytes_true(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=b"true")

        result = await is_trading_enabled(mock_redis)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_when_string_true(self, mock_redis):
        mock_redis.get = AsyncMock(return_value="true")

        result = await is_trading_enabled(mock_redis)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_case_insensitive(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=b"TRUE")

        result = await is_trading_enabled(mock_redis)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_false_string(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=b"false")

        result = await is_trading_enabled(mock_redis)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_other_value(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=b"invalid")

        result = await is_trading_enabled(mock_redis)

        assert result is False


class TestSetTradingEnabled:
    """Tests for set_trading_enabled function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.set = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_set_enabled_true(self, mock_redis):
        await set_trading_enabled(mock_redis, True)

        mock_redis.set.assert_called_once_with(TRADING_ENABLED_KEY, "true")

    @pytest.mark.asyncio
    async def test_set_enabled_false(self, mock_redis):
        await set_trading_enabled(mock_redis, False)

        mock_redis.set.assert_called_once_with(TRADING_ENABLED_KEY, "false")


class TestToggleTrading:
    """Tests for toggle_trading function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.get = AsyncMock()
        redis.set = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_toggle_from_disabled_to_enabled(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)

        result = await toggle_trading(mock_redis)

        assert result is True
        mock_redis.set.assert_called_once_with(TRADING_ENABLED_KEY, "true")

    @pytest.mark.asyncio
    async def test_toggle_from_enabled_to_disabled(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=b"true")

        result = await toggle_trading(mock_redis)

        assert result is False
        mock_redis.set.assert_called_once_with(TRADING_ENABLED_KEY, "false")

    @pytest.mark.asyncio
    async def test_toggle_from_false_to_true(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=b"false")

        result = await toggle_trading(mock_redis)

        assert result is True


class TestParseTradingEnabledValue:
    """Tests for _parse_trading_enabled_value function."""

    def test_none_returns_false(self):
        result = _parse_trading_enabled_value(None)

        assert result is False

    def test_bytes_true(self):
        result = _parse_trading_enabled_value(b"true")

        assert result is True

    def test_string_true(self):
        result = _parse_trading_enabled_value("true")

        assert result is True

    def test_bytes_false(self):
        result = _parse_trading_enabled_value(b"false")

        assert result is False

    def test_string_false(self):
        result = _parse_trading_enabled_value("false")

        assert result is False


class TestTradingEnabledKey:
    """Tests for TRADING_ENABLED_KEY constant."""

    def test_key_value(self):
        assert TRADING_ENABLED_KEY == "config:trading:enabled"
