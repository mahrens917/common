"""Unit tests for human_readable_retrieval module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.probability_store.exceptions import (
    ProbabilityDataNotFoundError,
    ProbabilityStoreError,
)
from common.redis_protocol.probability_store.probabilityretrieval_helpers.human_readable_retrieval import (
    _decode_key_entry,
    _insert_probability_entry,
    _scan_probability_keys,
    get_probabilities_human_readable,
)


class TestScanProbabilityKeys:
    """Tests for _scan_probability_keys."""

    @pytest.mark.asyncio
    async def test_scans_all_pages(self) -> None:
        call_count = 0

        async def fake_scan(cursor, match, count):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (1, [b"key1"])
            return (0, [b"key2"])

        redis = MagicMock()
        redis.scan = fake_scan

        keys = await _scan_probability_keys(redis, "probabilities:BTC:")
        assert b"key1" in keys
        assert b"key2" in keys

    @pytest.mark.asyncio
    async def test_returns_empty_on_no_keys(self) -> None:
        async def fake_scan(cursor, match, count):
            return (0, [])

        redis = MagicMock()
        redis.scan = fake_scan

        keys = await _scan_probability_keys(redis, "probabilities:BTC:")
        assert keys == []


class TestDecodeKeyEntry:
    """Tests for _decode_key_entry."""

    def test_raises_on_empty_data(self) -> None:
        with patch(
            "common.redis_protocol.probability_store.probabilityretrieval_helpers.human_readable_retrieval.parse_probability_key",
            return_value=("2025-01-01", "call", "50000"),
        ):
            with pytest.raises(ProbabilityStoreError, match="Probability payload missing"):
                _decode_key_entry("some_key", {})

    def test_raises_on_missing_event_title(self) -> None:
        with (
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.human_readable_retrieval.parse_probability_key",
                return_value=("2025-01-01", "call", "50000"),
            ),
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.human_readable_retrieval.decode_probability_hash",
                return_value={"probability": 0.5},
            ),
        ):
            with pytest.raises(ProbabilityStoreError, match="Missing event_title"):
                _decode_key_entry("some_key", {"probability": "0.5"})

    def test_success(self) -> None:
        with (
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.human_readable_retrieval.parse_probability_key",
                return_value=("2025-01-01", "call", "50000"),
            ),
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.human_readable_retrieval.decode_probability_hash",
                return_value={"probability": 0.5, "event_title": "BTC above 50k"},
            ),
        ):
            expiry, event_title, strike_type, strike, data = _decode_key_entry("some_key", {"probability": "0.5"})

        assert expiry == "2025-01-01"
        assert event_title == "BTC above 50k"
        assert strike_type == "call"
        assert strike == "50000"


class TestInsertProbabilityEntry:
    """Tests for _insert_probability_entry."""

    def test_inserts_new_entry(self) -> None:
        result = {}
        _insert_probability_entry(result, "2025-01-01", "BTC above 50k", "call", "50000", {"p": 0.5})
        assert result["2025-01-01"]["BTC above 50k"]["call"]["50000"] == {"p": 0.5}

    def test_inserts_into_existing_expiry(self) -> None:
        result = {"2025-01-01": {}}
        _insert_probability_entry(result, "2025-01-01", "BTC above 50k", "call", "50000", {"p": 0.5})
        assert "BTC above 50k" in result["2025-01-01"]

    def test_inserts_multiple_strikes(self) -> None:
        result = {}
        _insert_probability_entry(result, "2025-01-01", "BTC above 50k", "call", "50000", {"p": 0.5})
        _insert_probability_entry(result, "2025-01-01", "BTC above 50k", "call", "60000", {"p": 0.3})
        assert "50000" in result["2025-01-01"]["BTC above 50k"]["call"]
        assert "60000" in result["2025-01-01"]["BTC above 50k"]["call"]


class TestGetProbabilitiesHumanReadable:
    """Tests for get_probabilities_human_readable."""

    @pytest.mark.asyncio
    async def test_raises_on_no_keys(self) -> None:
        with patch(
            "common.redis_protocol.probability_store.probabilityretrieval_helpers.human_readable_retrieval._scan_probability_keys",
            new=AsyncMock(return_value=[]),
        ):
            redis = MagicMock()
            with pytest.raises(ProbabilityDataNotFoundError):
                await get_probabilities_human_readable(redis, "BTC")

    @pytest.mark.asyncio
    async def test_raises_on_redis_error(self) -> None:
        import redis as redis_lib

        with patch(
            "common.redis_protocol.probability_store.probabilityretrieval_helpers.human_readable_retrieval._scan_probability_keys",
            new=AsyncMock(side_effect=redis_lib.exceptions.ConnectionError("fail")),
        ):
            redis_client = MagicMock()
            with pytest.raises(ProbabilityStoreError, match="Redis error"):
                await get_probabilities_human_readable(redis_client, "BTC")

    @pytest.mark.asyncio
    async def test_returns_grouped_result(self) -> None:
        raw_keys = [b"probabilities:BTC:2025-01-01:call:50000"]
        hash_data = {"probability": 0.5, "event_title": "BTC above 50k"}
        pipeline = MagicMock()

        async def fake_ensure(coro):
            import inspect

            if inspect.iscoroutine(coro):
                coro.close()
            return [{"probability": "0.5"}]

        with (
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.human_readable_retrieval._scan_probability_keys",
                new=AsyncMock(return_value=raw_keys),
            ),
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.human_readable_retrieval.ensure_awaitable",
                side_effect=fake_ensure,
            ),
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.human_readable_retrieval._decode_key_entry",
                return_value=("2025-01-01", "BTC above 50k", "call", "50000", hash_data),
            ),
            patch(
                "common.redis_protocol.probability_store.probabilityretrieval_helpers.human_readable_retrieval.log_human_readable_summary",
            ),
        ):
            redis_client = MagicMock()
            redis_client.pipeline.return_value = pipeline

            result = await get_probabilities_human_readable(redis_client, "BTC")

        assert "2025-01-01" in result
        assert "BTC above 50k" in result["2025-01-01"]
