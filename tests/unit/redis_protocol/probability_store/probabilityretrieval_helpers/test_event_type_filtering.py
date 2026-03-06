"""Unit tests for event_type_filtering module."""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.probability_store.exceptions import ProbabilityStoreError
from common.redis_protocol.probability_store.probabilityretrieval_helpers.event_type_filtering import (
    filter_keys_by_event_type,
    get_probabilities_by_event_type,
)


def _close_if_coro(obj):
    if inspect.iscoroutine(obj):
        obj.close()


class TestFilterKeysByEventType:
    """Tests for filter_keys_by_event_type."""

    @pytest.mark.asyncio
    async def test_returns_empty_on_empty_keys(self) -> None:
        redis = MagicMock()
        result = await filter_keys_by_event_type(redis, [], "btc_above_50k")
        assert result == []

    @pytest.mark.asyncio
    async def test_filters_matching_keys(self) -> None:
        async def fake_ensure(coro):
            _close_if_coro(coro)
            return [b"btc_above_50k", b"other_event"]

        pipeline = MagicMock()
        pipeline.hget = MagicMock()
        pipeline.execute = MagicMock(return_value=[])
        redis = MagicMock()
        redis.pipeline.return_value = pipeline

        with patch(
            "common.redis_protocol.probability_store.probabilityretrieval_helpers.event_type_filtering.ensure_awaitable",
            side_effect=fake_ensure,
        ):
            result = await filter_keys_by_event_type(redis, [b"key1", b"key2"], "btc_above_50k")

        assert result == ["key1"]

    @pytest.mark.asyncio
    async def test_skips_empty_event_type(self) -> None:
        async def fake_ensure(coro):
            _close_if_coro(coro)
            return [None, b""]

        pipeline = MagicMock()
        pipeline.hget = MagicMock()
        pipeline.execute = MagicMock(return_value=[])
        redis = MagicMock()
        redis.pipeline.return_value = pipeline

        with patch(
            "common.redis_protocol.probability_store.probabilityretrieval_helpers.event_type_filtering.ensure_awaitable",
            side_effect=fake_ensure,
        ):
            result = await filter_keys_by_event_type(redis, [b"key1", b"key2"], "btc_above_50k")

        assert result == []


class TestGetProbabilitiesByEventType:
    """Tests for get_probabilities_by_event_type."""

    @pytest.mark.asyncio
    async def test_raises_on_no_data(self) -> None:
        async def fake_ensure(coro):
            _close_if_coro(coro)
            return (0, [])

        redis = MagicMock()

        with (
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.event_type_filtering.ensure_awaitable",
                side_effect=fake_ensure,
            ),
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.event_type_filtering.filter_keys_by_event_type",
                new=AsyncMock(return_value=[]),
            ),
        ):
            with pytest.raises(ProbabilityStoreError, match="No data found for event type"):
                await get_probabilities_by_event_type(redis, "BTC", "btc_above_50k")

    @pytest.mark.asyncio
    async def test_raises_on_redis_error(self) -> None:
        import redis as redis_lib

        async def fail_ensure(coro):
            _close_if_coro(coro)
            raise redis_lib.exceptions.ConnectionError("fail")

        with patch(
            "common.redis_protocol.probability_store.probabilityretrieval_helpers.event_type_filtering.ensure_awaitable",
            side_effect=fail_ensure,
        ):
            redis_client = MagicMock()
            with pytest.raises(ProbabilityStoreError, match="Redis error"):
                await get_probabilities_by_event_type(redis_client, "BTC", "btc_above_50k")

    @pytest.mark.asyncio
    async def test_returns_sorted_probabilities(self) -> None:
        keys = ["probabilities:BTC:2025-01-01:call:50000"]
        raw_hash_data = {b"probability": b"0.5", b"event_type": b"btc_above_50k"}

        pipeline = MagicMock()

        call_count = 0

        async def fake_ensure(coro):
            nonlocal call_count
            _close_if_coro(coro)
            call_count += 1
            if call_count == 1:
                return (0, [b"probabilities:BTC:2025-01-01:call:50000"])
            return [raw_hash_data]

        with (
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.event_type_filtering.ensure_awaitable",
                side_effect=fake_ensure,
            ),
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.event_type_filtering.filter_keys_by_event_type",
                new=AsyncMock(return_value=keys),
            ),
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.event_type_filtering.parse_probability_key",
                return_value=("2025-01-01", "call", "50000"),
            ),
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.event_type_filtering.decode_probability_hash",
                return_value={"probability": 0.5},
            ),
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.event_type_filtering.sort_probabilities_by_expiry_and_strike_grouped",
                return_value={"2025-01-01": {"call": {"50000": {"probability": 0.5}}}},
            ),
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.event_type_filtering.log_event_type_summary",
            ),
        ):
            redis_client = MagicMock()
            redis_client.pipeline.return_value = pipeline
            result = await get_probabilities_by_event_type(redis_client, "BTC", "btc_above_50k")

        assert "2025-01-01" in result
