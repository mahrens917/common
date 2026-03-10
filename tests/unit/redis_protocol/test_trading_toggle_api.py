"""Tests for per-algo trading_toggle_api module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.trading_toggle_api import (
    ALGO_TRADING_KEY_PREFIX,
    SIGNAL_COUNT_KEY_PREFIX,
    AlgoTradingConfig,
    _algo_config_key,
    _algo_key,
    _parse_bool,
    _signal_count_key,
    _validate_positive_int,
    delete_old_cooldown_keys,
    get_algo_max_contracts,
    get_algo_sample_rate,
    get_all_algo_trading_config,
    get_all_algo_trading_states,
    get_signal_counts,
    increment_signal_count,
    initialize_algo_trading_defaults,
    is_algo_trading_enabled,
    reset_daily_counts,
    set_algo_max_contracts,
    set_algo_sample_rate,
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
        algos = ["peak", "edge", "crossarb"]

        result = await get_all_algo_trading_states(mock_redis, algos, "paper")

        assert result == {"peak": True, "edge": False, "crossarb": True}

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
        # 2 algos * 2 modes * 3 fields (enabled + sample_rate + max_contracts) = 12
        pipe.execute = AsyncMock(return_value=[True] * 12)
        redis.pipeline = MagicMock(return_value=pipe)

        await initialize_algo_trading_defaults(redis, ["peak", "edge"])

        setnx_calls = pipe.setnx.call_args_list
        _FIELDS_PER_MODE = 3
        _MODES = 2
        expected_count = len(["peak", "edge"]) * _MODES * _FIELDS_PER_MODE
        assert len(setnx_calls) == expected_count

        # peak paper: enabled, sample_rate, max_contracts
        assert setnx_calls[0].args == ("config:trading:algo:peak:paper", "true")
        assert setnx_calls[1].args == ("config:trading:algo:peak:paper:sample_rate", "100")
        assert setnx_calls[2].args == ("config:trading:algo:peak:paper:max_contracts", "1")
        # peak live
        assert setnx_calls[3].args == ("config:trading:algo:peak:live", "false")
        assert setnx_calls[4].args == ("config:trading:algo:peak:live:sample_rate", "100")
        assert setnx_calls[5].args == ("config:trading:algo:peak:live:max_contracts", "1")
        # edge paper
        assert setnx_calls[6].args == ("config:trading:algo:edge:paper", "true")
        assert setnx_calls[7].args == ("config:trading:algo:edge:paper:sample_rate", "100")
        assert setnx_calls[8].args == ("config:trading:algo:edge:paper:max_contracts", "1")
        # edge live
        assert setnx_calls[9].args == ("config:trading:algo:edge:live", "false")
        assert setnx_calls[10].args == ("config:trading:algo:edge:live:sample_rate", "100")
        assert setnx_calls[11].args == ("config:trading:algo:edge:live:max_contracts", "1")


class TestAlgoConfigKey:
    """Tests for _algo_config_key helper."""

    def test_builds_sample_rate_key(self):
        result = _algo_config_key("peak", "paper", "sample_rate")
        assert result == "config:trading:algo:peak:paper:sample_rate"

    def test_builds_max_contracts_key(self):
        result = _algo_config_key("edge", "live", "max_contracts")
        assert result == "config:trading:algo:edge:live:max_contracts"


class TestSignalCountKey:
    """Tests for _signal_count_key helper."""

    def test_builds_signal_count_key(self):
        result = _signal_count_key("peak")
        assert result == "stats:signals:daily:peak"


class TestValidatePositiveInt:
    """Tests for _validate_positive_int helper."""

    def test_accepts_positive_int(self):
        _validate_positive_int(1, "field")
        _validate_positive_int(100, "field")

    def test_rejects_zero(self):
        with pytest.raises(ValueError, match="must be a positive integer"):
            _validate_positive_int(0, "sample_rate")

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="must be a positive integer"):
            _validate_positive_int(-5, "max_contracts")

    def test_rejects_bool_true(self):
        with pytest.raises(ValueError, match="must be a positive integer"):
            _validate_positive_int(True, "field")

    def test_rejects_bool_false(self):
        with pytest.raises(ValueError, match="must be a positive integer"):
            _validate_positive_int(False, "field")

    def test_rejects_float(self):
        with pytest.raises(ValueError, match="must be a positive integer"):
            _validate_positive_int(3.5, "field")

    def test_rejects_string(self):
        with pytest.raises(ValueError, match="must be a positive integer"):
            _validate_positive_int("10", "field")

    def test_error_message_includes_field_name(self):
        with pytest.raises(ValueError, match="sample_rate must be a positive integer"):
            _validate_positive_int(-1, "sample_rate")

    def test_error_message_includes_value(self):
        with pytest.raises(ValueError, match=r"got -3"):
            _validate_positive_int(-3, "field")


class TestGetAlgoSampleRate:
    """Tests for get_algo_sample_rate function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.get = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_returns_value_from_redis_bytes(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=b"50")

        result = await get_algo_sample_rate(mock_redis, "peak", "paper")

        assert result == 50
        mock_redis.get.assert_called_once_with("config:trading:algo:peak:paper:sample_rate")

    @pytest.mark.asyncio
    async def test_returns_value_from_redis_string(self, mock_redis):
        mock_redis.get = AsyncMock(return_value="200")

        result = await get_algo_sample_rate(mock_redis, "edge", "live")

        assert result == 200

    @pytest.mark.asyncio
    async def test_returns_default_when_key_missing(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)

        result = await get_algo_sample_rate(mock_redis, "weather", "paper")

        assert result == 100


class TestSetAlgoSampleRate:
    """Tests for set_algo_sample_rate function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.set = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_sets_sample_rate_value(self, mock_redis):
        await set_algo_sample_rate(mock_redis, "peak", "paper", 50)

        mock_redis.set.assert_called_once_with("config:trading:algo:peak:paper:sample_rate", "50")

    @pytest.mark.asyncio
    async def test_rejects_zero(self, mock_redis):
        with pytest.raises(ValueError, match="sample_rate must be a positive integer"):
            await set_algo_sample_rate(mock_redis, "peak", "paper", 0)

        mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejects_negative(self, mock_redis):
        with pytest.raises(ValueError, match="sample_rate must be a positive integer"):
            await set_algo_sample_rate(mock_redis, "peak", "live", -10)

        mock_redis.set.assert_not_called()


class TestGetAlgoMaxContracts:
    """Tests for get_algo_max_contracts function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.get = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_returns_value_from_redis_bytes(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=b"5")

        result = await get_algo_max_contracts(mock_redis, "peak", "paper")

        assert result == 5
        mock_redis.get.assert_called_once_with("config:trading:algo:peak:paper:max_contracts")

    @pytest.mark.asyncio
    async def test_returns_value_from_redis_string(self, mock_redis):
        mock_redis.get = AsyncMock(return_value="10")

        result = await get_algo_max_contracts(mock_redis, "edge", "live")

        assert result == 10

    @pytest.mark.asyncio
    async def test_returns_default_when_key_missing(self, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)

        result = await get_algo_max_contracts(mock_redis, "weather", "live")

        assert result == 1


class TestSetAlgoMaxContracts:
    """Tests for set_algo_max_contracts function."""

    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis.set = AsyncMock()
        return redis

    @pytest.mark.asyncio
    async def test_sets_max_contracts_value(self, mock_redis):
        await set_algo_max_contracts(mock_redis, "peak", "live", 5)

        mock_redis.set.assert_called_once_with("config:trading:algo:peak:live:max_contracts", "5")

    @pytest.mark.asyncio
    async def test_rejects_zero(self, mock_redis):
        with pytest.raises(ValueError, match="max_contracts must be a positive integer"):
            await set_algo_max_contracts(mock_redis, "peak", "paper", 0)

        mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejects_negative(self, mock_redis):
        with pytest.raises(ValueError, match="max_contracts must be a positive integer"):
            await set_algo_max_contracts(mock_redis, "peak", "live", -1)

        mock_redis.set.assert_not_called()


class TestGetAllAlgoTradingConfig:
    """Tests for get_all_algo_trading_config function."""

    @pytest.mark.asyncio
    async def test_returns_full_config_for_all_algos(self):
        redis = MagicMock()
        pipe = MagicMock()
        pipe.get = MagicMock()
        # 2 algos * 3 fields = 6 pipeline results
        # peak: enabled=true, sample_rate=50, max_contracts=5
        # edge: enabled=false, sample_rate=200, max_contracts=3
        pipe.execute = AsyncMock(
            return_value=[
                b"true",
                b"50",
                b"5",
                b"false",
                b"200",
                b"3",
            ]
        )
        redis.pipeline = MagicMock(return_value=pipe)

        result = await get_all_algo_trading_config(redis, ["peak", "edge"], "paper")

        assert result == {
            "peak": AlgoTradingConfig(enabled=True, sample_rate=50, max_contracts=5),
            "edge": AlgoTradingConfig(enabled=False, sample_rate=200, max_contracts=3),
        }

    @pytest.mark.asyncio
    async def test_uses_defaults_for_missing_keys(self):
        redis = MagicMock()
        pipe = MagicMock()
        pipe.get = MagicMock()
        # all None values: use mode default for enabled, 100 for sample_rate, 1 for max_contracts
        pipe.execute = AsyncMock(return_value=[None, None, None])
        redis.pipeline = MagicMock(return_value=pipe)

        result = await get_all_algo_trading_config(redis, ["weather"], "paper")

        assert result == {
            "weather": AlgoTradingConfig(enabled=True, sample_rate=100, max_contracts=1),
        }

    @pytest.mark.asyncio
    async def test_uses_live_mode_defaults_for_missing_keys(self):
        redis = MagicMock()
        pipe = MagicMock()
        pipe.get = MagicMock()
        pipe.execute = AsyncMock(return_value=[None, None, None])
        redis.pipeline = MagicMock(return_value=pipe)

        result = await get_all_algo_trading_config(redis, ["peak"], "live")

        assert result == {
            "peak": AlgoTradingConfig(enabled=False, sample_rate=100, max_contracts=1),
        }

    @pytest.mark.asyncio
    async def test_mixed_present_and_missing_fields(self):
        redis = MagicMock()
        pipe = MagicMock()
        pipe.get = MagicMock()
        # enabled is set, sample_rate missing, max_contracts is set
        pipe.execute = AsyncMock(return_value=[b"true", None, b"10"])
        redis.pipeline = MagicMock(return_value=pipe)

        result = await get_all_algo_trading_config(redis, ["peak"], "live")

        assert result == {
            "peak": AlgoTradingConfig(enabled=True, sample_rate=100, max_contracts=10),
        }

    @pytest.mark.asyncio
    async def test_pipeline_issues_three_gets_per_algo(self):
        redis = MagicMock()
        pipe = MagicMock()
        pipe.get = MagicMock()
        pipe.execute = AsyncMock(return_value=[b"true", b"50", b"5"])
        redis.pipeline = MagicMock(return_value=pipe)

        await get_all_algo_trading_config(redis, ["peak"], "paper")

        assert pipe.get.call_count == 3
        pipe.get.assert_any_call("config:trading:algo:peak:paper")
        pipe.get.assert_any_call("config:trading:algo:peak:paper:sample_rate")
        pipe.get.assert_any_call("config:trading:algo:peak:paper:max_contracts")

    @pytest.mark.asyncio
    async def test_empty_algos_list(self):
        redis = MagicMock()
        pipe = MagicMock()
        pipe.get = MagicMock()
        pipe.execute = AsyncMock(return_value=[])
        redis.pipeline = MagicMock(return_value=pipe)

        result = await get_all_algo_trading_config(redis, [], "paper")

        assert result == {}


class TestIncrementSignalCount:
    """Tests for increment_signal_count function."""

    @pytest.mark.asyncio
    async def test_returns_rolling_24h_count(self):
        pipe = MagicMock()
        pipe.zadd = MagicMock()
        pipe.zremrangebyscore = MagicMock()
        pipe.zcard = MagicMock()
        pipe.execute = AsyncMock(return_value=[1, 0, 42])
        redis = MagicMock()
        redis.pipeline = MagicMock(return_value=pipe)

        result = await increment_signal_count(redis, "peak")

        assert result == 42
        pipe.zadd.assert_called_once()
        pipe.zremrangebyscore.assert_called_once()
        pipe.zcard.assert_called_once_with("stats:signals:daily:peak")

    @pytest.mark.asyncio
    async def test_zadd_uses_correct_key(self):
        pipe = MagicMock()
        pipe.zadd = MagicMock()
        pipe.zremrangebyscore = MagicMock()
        pipe.zcard = MagicMock()
        pipe.execute = AsyncMock(return_value=[1, 0, 1])
        redis = MagicMock()
        redis.pipeline = MagicMock(return_value=pipe)

        await increment_signal_count(redis, "edge")

        key_used = pipe.zadd.call_args[0][0]
        assert key_used == "stats:signals:daily:edge"


class TestGetSignalCounts:
    """Tests for get_signal_counts function."""

    @pytest.mark.asyncio
    async def test_returns_counts_for_all_algos(self):
        pipe = MagicMock()
        pipe.zcount = MagicMock()
        pipe.execute = AsyncMock(return_value=[150, 300, 0])
        redis = MagicMock()
        redis.pipeline = MagicMock(return_value=pipe)

        result = await get_signal_counts(redis, ["peak", "edge", "weather"])

        assert result == {"peak": 150, "edge": 300, "weather": 0}

    @pytest.mark.asyncio
    async def test_empty_algos_list(self):
        pipe = MagicMock()
        pipe.execute = AsyncMock(return_value=[])
        redis = MagicMock()
        redis.pipeline = MagicMock(return_value=pipe)

        result = await get_signal_counts(redis, [])

        assert result == {}


class TestDeleteOldCooldownKeys:
    """Tests for delete_old_cooldown_keys function."""

    @pytest.mark.asyncio
    async def test_deletes_cooldown_keys_for_all_algos_and_modes(self):
        redis = MagicMock()
        redis.delete = AsyncMock(return_value=4)

        result = await delete_old_cooldown_keys(redis, ["peak", "edge"])

        assert result == 4
        redis.delete.assert_called_once_with(
            "config:trading:algo:peak:paper:cooldown_minutes",
            "config:trading:algo:peak:live:cooldown_minutes",
            "config:trading:algo:edge:paper:cooldown_minutes",
            "config:trading:algo:edge:live:cooldown_minutes",
        )

    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_algos(self):
        redis = MagicMock()

        result = await delete_old_cooldown_keys(redis, [])

        assert result == 0


class TestAlgoTradingConfig:
    """Tests for AlgoTradingConfig dataclass."""

    def test_frozen_dataclass(self):
        config = AlgoTradingConfig(enabled=True, sample_rate=50, max_contracts=5)
        assert config.enabled is True
        assert config.sample_rate == 50
        assert config.max_contracts == 5

    def test_frozen_raises_on_mutation(self):
        config = AlgoTradingConfig(enabled=True, sample_rate=50, max_contracts=5)
        with pytest.raises(AttributeError):
            config.enabled = False

    def test_equality(self):
        config_a = AlgoTradingConfig(enabled=True, sample_rate=100, max_contracts=1)
        config_b = AlgoTradingConfig(enabled=True, sample_rate=100, max_contracts=1)
        assert config_a == config_b

    def test_inequality(self):
        config_a = AlgoTradingConfig(enabled=True, sample_rate=100, max_contracts=1)
        config_b = AlgoTradingConfig(enabled=False, sample_rate=100, max_contracts=1)
        assert config_a != config_b


class TestAlgoTradingKeyPrefix:
    """Tests for ALGO_TRADING_KEY_PREFIX constant."""

    def test_key_prefix(self):
        assert ALGO_TRADING_KEY_PREFIX == "config:trading:algo"


class TestResetDailyCounts:
    """Tests for reset_daily_counts function."""

    @pytest.mark.asyncio
    async def test_deletes_signal_and_trade_count_keys(self):
        redis = MagicMock()
        redis.delete = AsyncMock(return_value=4)

        result = await reset_daily_counts(redis, ["peak", "edge"])

        assert result == 4
        redis.delete.assert_called_once_with(
            "stats:signals:daily:peak",
            "stats:signals:daily:edge",
            "stats:validated:daily:peak",
            "stats:validated:daily:edge",
            "stats:trades:daily:peak",
            "stats:trades:daily:edge",
        )

    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_algos(self):
        redis = MagicMock()

        result = await reset_daily_counts(redis, [])

        assert result == 0


class TestSignalCountKeyPrefix:
    """Tests for SIGNAL_COUNT_KEY_PREFIX constant."""

    def test_key_prefix(self):
        assert SIGNAL_COUNT_KEY_PREFIX == "stats:signals:daily"
