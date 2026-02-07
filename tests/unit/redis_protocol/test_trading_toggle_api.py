"""Tests for per-algo trading_toggle_api module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.trading_toggle_api import (
    ALGO_TRADING_KEY_PREFIX,
    _algo_key,
    _parse_bool,
    get_all_algo_trading_states,
    initialize_algo_trading_defaults,
    is_algo_trading_enabled,
    set_algo_trading_enabled,
    set_all_algo_trading_enabled,
    toggle_algo_trading,
)


class TestAlgoKey:
    """Tests for _algo_key helper."""

    def test_builds_correct_key(self):
        assert _algo_key("peak", "paper") == "config:trading:algo:peak:paper"

    def test_builds_live_key(self):
        assert _algo_key("edge", "live") == "config:trading:algo:edge:live"


class TestParseBool:
    """Tests for _parse_bool helper."""

    def test_none_paper_defaults_true(self):
        assert _parse_bool(None, "paper") is True

    def test_none_live_defaults_false(self):
        assert _parse_bool(None, "live") is False

    def test_bytes_true(self):
        assert _parse_bool(b"true", "live") is True

    def test_bytes_false(self):
        assert _parse_bool(b"false", "paper") is False

    def test_string_true(self):
        assert _parse_bool("true", "live") is True

    def test_case_insensitive(self):
        assert _parse_bool(b"TRUE", "live") is True

    def test_invalid_value_returns_false(self):
        assert _parse_bool(b"invalid", "paper") is False


class TestIsAlgoTradingEnabled:
    """Tests for is_algo_trading_enabled function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.get = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_returns_default_when_key_missing_paper(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)

        result = await is_algo_trading_enabled(mock_redis, "peak", "paper")

        assert result is True
        mock_redis.get.assert_called_once_with("config:trading:algo:peak:paper")

    @pytest.mark.asyncio
    async def test_returns_default_when_key_missing_live(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)

        result = await is_algo_trading_enabled(mock_redis, "peak", "live")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_set(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=b"true")

        result = await is_algo_trading_enabled(mock_redis, "peak", "live")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_set(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=b"false")

        result = await is_algo_trading_enabled(mock_redis, "peak", "paper")

        assert result is False


class TestSetAlgoTradingEnabled:
    """Tests for set_algo_trading_enabled function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.set = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_set_enabled_true(self, mock_redis):
        await set_algo_trading_enabled(mock_redis, "peak", "live", True)

        mock_redis.set.assert_called_once_with("config:trading:algo:peak:live", "true")

    @pytest.mark.asyncio
    async def test_set_enabled_false(self, mock_redis):
        await set_algo_trading_enabled(mock_redis, "edge", "paper", False)

        mock_redis.set.assert_called_once_with("config:trading:algo:edge:paper", "false")


class TestToggleAlgoTrading:
    """Tests for toggle_algo_trading function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.get = AsyncMock()
        redis.set = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_toggle_from_off_to_on(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=b"false")

        result = await toggle_algo_trading(mock_redis, "peak", "live")

        assert result is True
        mock_redis.set.assert_called_once_with("config:trading:algo:peak:live", "true")

    @pytest.mark.asyncio
    async def test_toggle_from_on_to_off(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=b"true")

        result = await toggle_algo_trading(mock_redis, "peak", "paper")

        assert result is False

    @pytest.mark.asyncio
    async def test_toggle_from_missing_paper_default(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)

        result = await toggle_algo_trading(mock_redis, "peak", "paper")

        assert result is False


class TestGetAllAlgoTradingStates:
    """Tests for get_all_algo_trading_states function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        pipe = MagicMock()
        pipe.get = MagicMock()
        pipe.execute = AsyncMock(return_value=[b"true", b"false", None])
        redis.pipeline = MagicMock(return_value=pipe)
        return redis

    @pytest.mark.asyncio
    async def test_returns_dict_of_states(self, mock_redis):
        algos = ["peak", "edge", "whale"]

        result = await get_all_algo_trading_states(mock_redis, algos, "paper")

        assert result == {"peak": True, "edge": False, "whale": True}

    @pytest.mark.asyncio
    async def test_live_mode_defaults(self):
        redis = MagicMock()
        pipe = MagicMock()
        pipe.get = MagicMock()
        pipe.execute = AsyncMock(return_value=[None, None])
        redis.pipeline = MagicMock(return_value=pipe)

        result = await get_all_algo_trading_states(redis, ["peak", "edge"], "live")

        assert result == {"peak": False, "edge": False}


class TestSetAllAlgoTradingEnabled:
    """Tests for set_all_algo_trading_enabled function."""

    @pytest.mark.asyncio
    async def test_sets_all_algos(self):
        redis = MagicMock()
        pipe = MagicMock()
        pipe.set = MagicMock()
        pipe.execute = AsyncMock(return_value=[True, True])
        redis.pipeline = MagicMock(return_value=pipe)

        await set_all_algo_trading_enabled(redis, ["peak", "edge"], "live", False)

        expected_calls = [
            (("config:trading:algo:peak:live", "false"),),
            (("config:trading:algo:edge:live", "false"),),
        ]
        assert pipe.set.call_count == 2
        for call, expected in zip(pipe.set.call_args_list, expected_calls):
            assert call.args == expected[0]


class TestInitializeAlgoTradingDefaults:
    """Tests for initialize_algo_trading_defaults function."""

    @pytest.mark.asyncio
    async def test_initializes_defaults(self):
        redis = MagicMock()
        pipe = MagicMock()
        pipe.setnx = MagicMock()
        pipe.execute = AsyncMock(return_value=[True] * 4)
        redis.pipeline = MagicMock(return_value=pipe)

        await initialize_algo_trading_defaults(redis, ["peak", "edge"])

        setnx_calls = pipe.setnx.call_args_list
        # 2 algos * 2 modes (paper + live) = 4 setnx calls
        assert len(setnx_calls) == len(["peak", "edge"]) * len(["paper", "live"])
        assert setnx_calls[0].args == ("config:trading:algo:peak:paper", "true")
        assert setnx_calls[1].args == ("config:trading:algo:peak:live", "false")
        assert setnx_calls[2].args == ("config:trading:algo:edge:paper", "true")
        assert setnx_calls[3].args == ("config:trading:algo:edge:live", "false")


class TestAlgoTradingKeyPrefix:
    """Tests for ALGO_TRADING_KEY_PREFIX constant."""

    def test_key_prefix(self):
        assert ALGO_TRADING_KEY_PREFIX == "config:trading:algo"
