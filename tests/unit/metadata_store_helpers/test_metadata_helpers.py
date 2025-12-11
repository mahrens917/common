import asyncio
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from common.exceptions import DataError
from common.metadata_store_helpers.history_manager import HistoryManager
from common.metadata_store_helpers.metadata_reader import MetadataReader
from common.metadata_store_helpers.metadata_writer import MetadataWriter

DEFAULT_TOTAL_MESSAGE_COUNT = 500
from common.metadata_store_helpers.operations_facade import OperationsFacade
from common.metadata_store_helpers.reader_operations import (
    fetch_hash_data,
    fetch_hash_field,
    fetch_service_keys,
)
from common.metadata_store_helpers.writer_operations import (
    increment_metadata_counter,
    update_hash_fields,
)


class TestReaderOperations(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_hash_data_success(self):
        mock_client = AsyncMock()
        mock_client.hgetall.return_value = {"field": "value"}

        result = await fetch_hash_data(mock_client, "key", "context")
        assert result == {"field": "value"}

    async def test_fetch_hash_data_empty(self):
        mock_client = AsyncMock()
        mock_client.hgetall.return_value = {}

        result = await fetch_hash_data(mock_client, "key", "context")
        assert result is None

    async def test_fetch_service_keys_success(self):
        mock_client = AsyncMock()
        mock_client.keys.return_value = [b"key1", "key2"]

        result = await fetch_service_keys(mock_client, "pattern*")
        assert result == {"key1", "key2"}

    async def test_fetch_hash_field_success(self):
        mock_client = AsyncMock()
        mock_client.hget.return_value = "value"

        result = await fetch_hash_field(mock_client, "key", "field", "context")
        assert result == "value"


class TestWriterOperations(unittest.IsolatedAsyncioTestCase):
    async def test_increment_metadata_counter_success(self):
        mock_client = AsyncMock()
        mock_pipeline = MagicMock()
        # execute is async
        mock_pipeline.execute = AsyncMock(return_value=[1, 1, 1, 1, 1])

        # client.pipeline() is synchronous
        mock_client.pipeline = Mock(return_value=mock_pipeline)

        result = await increment_metadata_counter(mock_client, "meta:key", "global:key", "service", 5)
        assert result is True
        mock_pipeline.hincrby.assert_any_call("meta:key", "total_count", 5)
        mock_pipeline.hincrby.assert_any_call("global:key", "total_messages", 5)
        mock_pipeline.expire.assert_called()
        mock_pipeline.execute.assert_awaited_once()

    async def test_update_hash_fields_success(self):
        mock_client = AsyncMock()

        result = await update_hash_fields(mock_client, "key", "service", {"field": "value"})
        assert result is True
        mock_client.hset.assert_awaited_once_with("key", mapping={"field": "value"})
        mock_client.expire.assert_awaited_once()


class TestMetadataReader(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.reader = MetadataReader("meta:", "global:stats")
        self.mock_client = AsyncMock()

    async def test_get_service_metadata_success(self):
        self.mock_client.hgetall.return_value = {
            "total_count": "100",
            "last_activity": "1234567890.0",
            "messages_last_hour": "10",
            "messages_last_minute": "1",
            "messages_last_65_minutes": "15",
        }

        metadata = await self.reader.get_service_metadata(self.mock_client, "service1")
        assert metadata.service_name == "service1"
        assert metadata.total_message_count == 100
        assert metadata.last_activity_timestamp == 1234567890.0
        assert metadata.messages_last_hour == 10

    async def test_get_service_metadata_none(self):
        self.mock_client.hgetall.return_value = {}
        metadata = await self.reader.get_service_metadata(self.mock_client, "service1")
        assert metadata is None

    async def test_get_service_metadata_corrupt(self):
        self.mock_client.hgetall.return_value = {"total_count": "invalid"}
        with pytest.raises(DataError):
            await self.reader.get_service_metadata(self.mock_client, "service1")

    async def test_get_all_services(self):
        self.mock_client.keys.return_value = [b"meta:service1", "meta:service2"]
        services = await self.reader.get_all_services(self.mock_client)
        assert services == {"service1", "service2"}

    async def test_get_total_message_count(self):
        self.mock_client.hget.return_value = str(DEFAULT_TOTAL_MESSAGE_COUNT)
        count = await self.reader.get_total_message_count(self.mock_client)
        assert count == DEFAULT_TOTAL_MESSAGE_COUNT

    async def test_get_total_message_count_none(self):
        self.mock_client.hget.return_value = None
        count = await self.reader.get_total_message_count(self.mock_client)
        assert count == 0

    async def test_get_total_message_count_invalid(self):
        self.mock_client.hget.return_value = "invalid"
        with pytest.raises(TypeError):
            await self.reader.get_total_message_count(self.mock_client)


class TestMetadataWriter(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.writer = MetadataWriter("meta:", "global:stats")
        self.mock_client = AsyncMock()

    async def test_increment_service_count(self):
        with patch(
            "common.metadata_store_helpers.metadata_writer.increment_metadata_counter",
            new_callable=AsyncMock,
        ) as mock_incr:
            mock_incr.return_value = True
            result = await self.writer.increment_service_count(self.mock_client, "service1", 5)
            assert result is True
            mock_incr.assert_awaited_with(self.mock_client, "meta:service1", "global:stats", "service1", 5)

    async def test_update_time_window_counts(self):
        with patch(
            "common.metadata_store_helpers.metadata_writer.update_hash_fields",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = True
            result = await self.writer.update_time_window_counts(self.mock_client, "service1", 10, 1)
            assert result is True
            mock_update.assert_awaited_with(
                self.mock_client,
                "meta:service1",
                "service1",
                {"messages_last_hour": "10", "messages_last_minute": "1"},
            )

    async def test_update_weather_time_window_counts(self):
        with patch(
            "common.metadata_store_helpers.metadata_writer.update_hash_fields",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = True
            result = await self.writer.update_weather_time_window_counts(self.mock_client, "service1", 10, 1, 15)
            assert result is True
            mock_update.assert_awaited_with(
                self.mock_client,
                "meta:service1",
                "service1",
                {
                    "messages_last_hour": "10",
                    "messages_last_minute": "1",
                    "messages_last_65_minutes": "15",
                },
            )

    async def test_initialize_service_count(self):
        with patch(
            "common.metadata_store_helpers.metadata_writer.update_hash_fields",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = True
            result = await self.writer.initialize_service_count(self.mock_client, "service1", 100)
            assert result is True
            # Check mapping contains correct fields
            args = mock_update.await_args[0]  # (client, key, service, mapping)
            mapping = args[3]
            assert mapping["total_count"] == "100"
            assert mapping["messages_last_hour"] == "0"


class TestHistoryManager(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.manager = HistoryManager()
        self.mock_client = AsyncMock()

    async def test_get_service_history_success(self):
        now = int(time.time())
        # Mock data: one recent, one old, one invalid
        self.mock_client.hgetall.return_value = {
            f"2023-01-01 12:00:00": "10",  # Should be filtered out by time (assuming tests run in 2025)
            # Let's construct timestamps relative to now
            datetime.fromtimestamp(now - 3600, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"): "20",
            datetime.fromtimestamp(now - 100, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"): b"30",
            "invalid_date": "40",
            "2023-01-01 12:00:00": "invalid_count",
        }

        # Override _load_history_hash to verify it calls hgetall
        # But we can rely on hgetall mock return

        history = await self.manager.get_service_history(self.mock_client, "service1", hours=2)

        # Expect 2 entries (recent ones)
        assert len(history) == 2
        assert history[0]["messages_per_minute"] == 20.0
        assert history[1]["messages_per_minute"] == 30.0

    async def test_get_service_history_empty(self):
        self.mock_client.hgetall.return_value = {}
        history = await self.manager.get_service_history(self.mock_client, "service1")
        assert history == []

    async def test_get_service_history_iso_format(self):
        now = int(time.time())
        ts_str = datetime.fromtimestamp(now, tz=timezone.utc).isoformat()
        self.mock_client.hgetall.return_value = {ts_str: "50"}

        history = await self.manager.get_service_history(self.mock_client, "service1")
        assert len(history) == 1
        assert history[0]["messages_per_minute"] == 50.0


class TestOperationsFacade(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.facade = OperationsFacade("meta:", "global:stats")
        self.mock_client = AsyncMock()

    async def test_delegation(self):
        # Test one method to ensure delegation works
        with patch.object(self.facade.reader, "get_service_metadata", new_callable=AsyncMock) as mock_get:
            await self.facade.get_service_metadata(self.mock_client, "s1")
            mock_get.assert_awaited_once()

        with patch.object(self.facade.writer, "increment_service_count", new_callable=AsyncMock) as mock_incr:
            await self.facade.increment_service_count(self.mock_client, "s1")
            mock_incr.assert_awaited_once()

        with patch.object(self.facade.history, "get_service_history", new_callable=AsyncMock) as mock_hist:
            await self.facade.get_service_history(self.mock_client, "s1")
            mock_hist.assert_awaited_once()
