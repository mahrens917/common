from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from common.redis_protocol.probability_store.exceptions import ProbabilityStoreError
from common.redis_protocol.probability_store.probabilityingestion_helpers.compact_store_helpers import (
    execute_storage_pipeline,
    handle_storage_errors,
    log_sample_fields,
)


class TestCompactStoreHelpers:
    @pytest.mark.asyncio
    async def test_execute_storage_pipeline_success(self):
        redis = AsyncMock()
        pipeline = MagicMock()

        # execute_pipeline returns list of results
        # We expect 1 + field_count operations
        # Let's say field_count = 2. So 3 operations.
        # results[0] is probably delete or something, results[1:] are sets.
        # successful_sets should be sum of bool(res) for res in results[1:]

        with patch(
            "common.redis_protocol.probability_store.pipeline.execute_pipeline"
        ) as mock_exec:
            mock_exec.return_value = [True, True, True]
            redis.hlen.return_value = 2

            await execute_storage_pipeline(redis, pipeline, "key", 2, "BTC")

            mock_exec.assert_awaited_once_with(pipeline)
            redis.hlen.assert_awaited_once_with("key")

    @pytest.mark.asyncio
    async def test_execute_storage_pipeline_mismatched_operations(self):
        redis = AsyncMock()
        pipeline = MagicMock()

        with patch(
            "common.redis_protocol.probability_store.pipeline.execute_pipeline"
        ) as mock_exec:
            mock_exec.return_value = [True]  # Expected 3

            with pytest.raises(ProbabilityStoreError, match="Redis pipeline returned"):
                await execute_storage_pipeline(redis, pipeline, "key", 2, "BTC")

    @pytest.mark.asyncio
    async def test_execute_storage_pipeline_failed_sets(self):
        redis = AsyncMock()
        pipeline = MagicMock()

        with patch(
            "common.redis_protocol.probability_store.pipeline.execute_pipeline"
        ) as mock_exec:
            # 3 results, but one set returned False/0
            mock_exec.return_value = [True, True, False]

            with pytest.raises(ProbabilityStoreError, match="Redis stored"):
                await execute_storage_pipeline(redis, pipeline, "key", 2, "BTC")

    @pytest.mark.asyncio
    async def test_execute_storage_pipeline_count_mismatch(self):
        redis = AsyncMock()
        pipeline = MagicMock()

        with patch(
            "common.redis_protocol.probability_store.pipeline.execute_pipeline"
        ) as mock_exec:
            mock_exec.return_value = [True, True, True]
            redis.hlen.return_value = 1  # Expected 2

            with pytest.raises(ProbabilityStoreError, match="Field count mismatch"):
                await execute_storage_pipeline(redis, pipeline, "key", 2, "BTC")

    def test_log_sample_fields(self):
        iterator = Mock()
        iterator.iter_probability_fields.return_value = [
            ("f1", "v1", True, "o1"),
            ("f2", "v2", False, "o2"),
        ]
        data = {}

        with patch(
            "common.redis_protocol.probability_store.probabilityingestion_helpers.compact_store_helpers.logger"
        ) as mock_logger:
            results = list(log_sample_fields(iterator, data))

            assert len(results) == 2
            assert results[0] == ("f1", "v1", True)
            assert mock_logger.info.call_count == 2

    @pytest.mark.asyncio
    async def test_handle_storage_errors_success(self):
        @handle_storage_errors("BTC")
        async def success():
            return "ok"

        assert await success() == "ok"

    @pytest.mark.asyncio
    async def test_handle_storage_errors_value_error(self):
        @handle_storage_errors("BTC")
        async def fail():
            raise ValueError("bad")

        with pytest.raises(ProbabilityStoreError, match="Failed to store probabilities for BTC"):
            await fail()

    @pytest.mark.asyncio
    async def test_handle_storage_errors_redis_error(self):
        import redis.exceptions

        @handle_storage_errors("BTC")
        async def fail():
            raise redis.exceptions.RedisError("redis fail")

        with pytest.raises(ProbabilityStoreError, match="Redis error"):
            await fail()
