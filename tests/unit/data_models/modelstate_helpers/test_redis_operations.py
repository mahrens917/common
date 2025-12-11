import unittest
from unittest.mock import AsyncMock, Mock

from common.data_models.modelstate_helpers.redis_operations import (
    ModelProbabilityCalculationError,
    ModelProbabilityDataUnavailable,
    extract_probability_from_key,
    fetch_probability_keys,
)


class TestRedisOperations(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_probability_keys_success(self):
        redis_client = Mock()
        redis_client.keys = AsyncMock(return_value=["probabilities:BTC:a:b:1", "probabilities:BTC:c:d:2"])

        keys = await fetch_probability_keys(redis_client, "BTC")
        assert keys == ["probabilities:BTC:a:b:1", "probabilities:BTC:c:d:2"]
        redis_client.keys.assert_called_with("probabilities:BTC:*")

    async def test_fetch_probability_keys_unavailable(self):
        redis_client = Mock()
        redis_client.keys = AsyncMock(return_value=[])

        with self.assertRaises(ModelProbabilityDataUnavailable):
            await fetch_probability_keys(redis_client, "BTC")

    async def test_fetch_probability_keys_error(self):
        redis_client = Mock()
        redis_client.keys = AsyncMock(side_effect=ValueError("Redis error"))

        with self.assertRaises(ModelProbabilityCalculationError):
            await fetch_probability_keys(redis_client, "BTC")

    async def test_extract_probability_from_key_success(self):
        redis_client = Mock()
        # Redis returns bytes keys
        redis_client.hgetall = AsyncMock(return_value={b"probability": b"0.75"})

        prob = await extract_probability_from_key(redis_client, "key")
        assert prob == 0.75

    async def test_extract_probability_from_key_redis_error(self):
        redis_client = Mock()
        # Redis errors now raise ModelProbabilityCalculationError (fail-fast)
        redis_client.hgetall = AsyncMock(side_effect=ConnectionError("Connection failed"))

        with self.assertRaises(ModelProbabilityCalculationError):
            await extract_probability_from_key(redis_client, "key")

    async def test_extract_probability_from_key_missing_field(self):
        redis_client = Mock()
        # Redis returns bytes keys - missing probability field returns None
        redis_client.hgetall = AsyncMock(return_value={b"other": b"value"})

        prob = await extract_probability_from_key(redis_client, "key")
        assert prob is None

    async def test_extract_probability_from_key_invalid_value(self):
        redis_client = Mock()
        # Invalid probability values now raise ModelProbabilityCalculationError (fail-fast)
        redis_client.hgetall = AsyncMock(return_value={b"probability": b"invalid"})

        with self.assertRaises(ModelProbabilityCalculationError):
            await extract_probability_from_key(redis_client, "key")
