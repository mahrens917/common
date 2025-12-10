"""Unit tests for redis_key_counter."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.optimized_status_reporter_helpers.redis_key_counter import (
    RedisKeyCounter,
)


class AsyncIteratorMock:
    """Helper to mock asynchronous iterators."""

    def __init__(self, items):
        self.items = items
        self.iterator = iter(items)
        # Store calls to assert later
        self.calls = []

    def __aiter__(self):  # This should not be async def
        self.calls.append("aiter")
        return self

    async def __anext__(self):
        self.calls.append("anext")
        try:
            return next(self.iterator)
        except StopIteration:
            raise StopAsyncIteration


class TestRedisKeyCounter:
    """Tests for RedisKeyCounter."""

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client."""
        client = Mock()
        # Ensure scan_iter returns an async iterable directly
        # The return_value of scan_iter should be configurable by tests
        return client

    @pytest.fixture
    def counter(self, mock_redis_client):
        """RedisKeyCounter instance."""
        return RedisKeyCounter(redis_client=mock_redis_client)

    @pytest.mark.asyncio
    async def test_count_keys_async_no_keys(self, counter, mock_redis_client):
        """Test count_keys_async returns 0 if no keys match."""
        mock_ai_mock = AsyncIteratorMock([])
        mock_redis_client.scan_iter.return_value = mock_ai_mock

        result = await counter.count_keys_async("test:*")
        mock_redis_client.scan_iter.assert_called_once_with(match="test:*", count=100)
        # Ensure the async iterator was used
        assert "aiter" in mock_ai_mock.calls

    @pytest.mark.asyncio
    async def test_count_keys_async_some_keys(self, counter, mock_redis_client):
        """Test count_keys_async returns correct count for matching keys."""
        mock_ai_mock = AsyncIteratorMock(["key1", "key2", "key3"])
        mock_redis_client.scan_iter.return_value = mock_ai_mock

        result = await counter.count_keys_async("test:*")
        assert result == 3
        mock_redis_client.scan_iter.assert_called_once_with(match="test:*", count=100)
        assert "aiter" in mock_ai_mock.calls
        assert mock_ai_mock.calls.count("anext") == 4  # 3 items + 1 StopAsyncIteration

    @pytest.mark.asyncio
    async def test_collect_key_counts_success(self, counter, mock_redis_client):
        """Test collect_key_counts successfully gathers all counts."""
        # Mocking get_schema_config
        with patch(
            "common.optimized_status_reporter_helpers.redis_key_counter.get_schema_config"
        ) as mock_get_schema_config:
            mock_schema = Mock()
            mock_schema.deribit_market_prefix = "deribit"
            mock_schema.kalshi_market_prefix = "kalshi"
            mock_get_schema_config.return_value = mock_schema

            # Mocking count_keys_async to return specific counts
            # Need to create AsyncMock instance here as counter.count_keys_async is a method
            counter.count_keys_async = AsyncMock(
                side_effect=[10, 20, 5, 15]
            )  # Deribit, Kalshi, CFB, Weather

            result = await counter.collect_key_counts()

            # Assert count_keys_async called for each pattern
            counter.count_keys_async.assert_any_call("deribit:*")
            counter.count_keys_async.assert_any_call("kalshi:*")
            counter.count_keys_async.assert_any_call("cfb:*")
            counter.count_keys_async.assert_any_call("weather:station:*")
            assert counter.count_keys_async.await_count == 4

            assert result == {
                "redis_deribit_keys": 10,
                "redis_kalshi_keys": 20,
                "redis_cfb_keys": 5,
                "redis_weather_keys": 15,
            }

    @pytest.mark.asyncio
    async def test_collect_key_counts_async_gather_exception(self, counter):
        """Test collect_key_counts handles exceptions during asyncio.gather."""
        with patch(
            "common.optimized_status_reporter_helpers.redis_key_counter.get_schema_config"
        ) as mock_get_schema_config:
            mock_schema = Mock()
            mock_schema.deribit_market_prefix = "deribit"
            mock_schema.kalshi_market_prefix = "kalshi"
            mock_get_schema_config.return_value = mock_schema

            # Make one of the count_keys_async calls raise an exception
            counter.count_keys_async = AsyncMock(
                side_effect=[10, Exception("Redis connection error"), 5, 15]
            )

            with pytest.raises(Exception, match="Redis connection error"):
                await counter.collect_key_counts()

    @pytest.mark.asyncio
    async def test_count_keys_async_no_redis_client(self):
        """Test count_keys_async raises TypeError if redis_client is None."""
        counter = RedisKeyCounter(redis_client=None)
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'scan_iter'"):
            await counter.count_keys_async("test:*")
