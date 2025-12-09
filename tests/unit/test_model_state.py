from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.data_models.model_state import ModelState
from src.common.data_models.modelstate_helpers import (
    ModelProbabilityCalculationError,
    ModelProbabilityDataUnavailable,
    ModelStateInitializationError,
    ModelStateUnavailableError,
)

_TEST_COUNT_3 = 3


@pytest.mark.asyncio
async def test_load_redis_returns_state_when_keys_found():
    redis_client = MagicMock()
    redis_client.keys = AsyncMock(return_value=["probabilities:BTC:20250101:call:40000"])

    with patch("src.common.data_models.model_state.ProbabilityStore", autospec=True) as store_cls:
        state = await ModelState.load_redis(redis_client, currency="btc")

    assert isinstance(state, ModelState)
    assert state.currency == "BTC"
    store_cls.assert_called_once_with(redis_client)
    redis_client.keys.assert_awaited_once_with("probabilities:BTC:*")


@pytest.mark.asyncio
async def test_load_redis_raises_when_no_keys():
    redis_client = MagicMock()
    redis_client.keys = AsyncMock(return_value=[])

    with patch("src.common.data_models.model_state.ProbabilityStore", autospec=True):
        with pytest.raises(ModelStateUnavailableError):
            await ModelState.load_redis(redis_client, currency="ETH")

    redis_client.keys.assert_awaited_once_with("probabilities:ETH:*")


@pytest.mark.asyncio
async def test_load_redis_raises_on_error():
    redis_client = MagicMock()
    redis_client.keys = AsyncMock(side_effect=RuntimeError("oops"))

    with patch("src.common.data_models.model_state.ProbabilityStore", autospec=True):
        with pytest.raises(ModelStateInitializationError):
            await ModelState.load_redis(redis_client, currency="btc")


def _make_probability_redis(keys: List[str], probability_map: dict[str, float]):
    redis_client = MagicMock()
    redis_client.keys = AsyncMock(return_value=keys)

    async def hgetall_side_effect(key):
        key_str = key.decode("utf-8") if isinstance(key, bytes) else key
        value = probability_map.get(key_str)
        if value is None:
            return {}
        return value

    redis_client.hgetall = AsyncMock(side_effect=hgetall_side_effect)
    return redis_client


@pytest.mark.asyncio
async def test_calculate_probability_sums_matching_keys():
    keys = [
        "probabilities:BTC:20250101:call:40000",  # within range
        b"probabilities:BTC:20250101:call:35000-45000",  # overlapping range
        "probabilities:BTC:20250101:call:>30000",  # threshold
        "probabilities:BTC:20250101:call:10000",  # outside range
        "probabilities:BTC:badkey",  # malformed
    ]

    probability_map = {
        "probabilities:BTC:20250101:call:40000": {"probability": "0.10"},
        "probabilities:BTC:20250101:call:35000-45000": {"probability": "0.20"},
        "probabilities:BTC:20250101:call:>30000": {"probability": "0.30"},
        "probabilities:BTC:20250101:call:10000": {"probability": "0.40"},
    }

    redis_client = _make_probability_redis(keys, probability_map)

    probability_store = MagicMock()
    probability_store._get_redis = AsyncMock(return_value=redis_client)

    state = ModelState(probability_store, currency="BTC")

    probability = await state.calculate_probability(35000, 50000, time_to_expiry=0.5)

    assert probability == pytest.approx(0.60)
    redis_client.keys.assert_awaited_once_with("probabilities:BTC:*")
    assert redis_client.hgetall.await_count >= _TEST_COUNT_3


@pytest.mark.asyncio
async def test_calculate_probability_raises_when_no_keys():
    redis_client = MagicMock()
    redis_client.keys = AsyncMock(return_value=[])
    redis_client.hgetall = AsyncMock()

    probability_store = MagicMock()
    probability_store._get_redis = AsyncMock(return_value=redis_client)

    state = ModelState(probability_store, currency="ETH")

    with pytest.raises(ModelProbabilityDataUnavailable):
        await state.calculate_probability(1000, 2000, time_to_expiry=0.1)
    redis_client.keys.assert_awaited_once_with("probabilities:ETH:*")
    redis_client.hgetall.assert_not_called()


@pytest.mark.asyncio
async def test_calculate_probability_raises_on_error():
    probability_store = MagicMock()
    probability_store._get_redis = AsyncMock(side_effect=RuntimeError("redis down"))

    state = ModelState(probability_store, currency="BTC")

    with pytest.raises(ModelProbabilityCalculationError):
        await state.calculate_probability(1000, 2000, time_to_expiry=0.1)
