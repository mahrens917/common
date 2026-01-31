import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from common.exceptions import DataError
from common.metadata_store_auto_updater_helpers.metadata_initializer import MetadataInitializer


class TestMetadataInitializer:
    @pytest.fixture
    def metadata_store(self):
        return AsyncMock()

    @pytest.fixture
    def mock_redis(self):
        client = AsyncMock()
        client.keys = AsyncMock(return_value=[])
        client.type = AsyncMock(return_value="zset")
        client.zcard = AsyncMock(return_value=5)
        return client

    @pytest.fixture
    def initializer(self, metadata_store, mock_redis):
        return MetadataInitializer(metadata_store, mock_redis)

    @pytest.mark.asyncio
    async def test_initialize_from_existing_keys_success(self, initializer, mock_redis, metadata_store):
        mock_redis.keys.return_value = [b"history:service1", "history:service2", "history:invalid"]

        # Mock extract_service_name to return None for 'invalid'
        def mock_extractor(key):
            if "invalid" in key:
                return None
            return key.split(":")[1]

        with patch.object(initializer._service_name_extractor, "extract_service_name", side_effect=mock_extractor):
            await initializer.initialize_from_existing_keys()

            assert metadata_store.initialize_service_count.call_count == 2
            metadata_store.initialize_service_count.assert_any_call("service1", 5)
            metadata_store.initialize_service_count.assert_any_call("service2", 5)

    @pytest.mark.asyncio
    async def test_initialize_no_client(self, initializer):
        initializer.redis_client = None
        # Should log error but not crash completely?
        # The code raises DataError inside try block, which is caught by REDIS_ERRORS (Exception).
        # So it logs error and finishes.
        with patch("common.metadata_store_auto_updater_helpers.metadata_initializer.logger") as mock_logger:
            await initializer.initialize_from_existing_keys()
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_ensure_hash_history_key_invalid_type(self, initializer, mock_redis):
        mock_redis.keys.return_value = ["history:service1"]
        mock_redis.type.return_value = b"string"

        with patch.object(initializer._service_name_extractor, "extract_service_name", return_value="service1"):
            await initializer.initialize_from_existing_keys()

            mock_redis.delete.assert_called_once_with("history:service1")
            mock_redis.zcard.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_hash_history_key_none_type(self, initializer, mock_redis):
        mock_redis.keys.return_value = ["history:service1"]
        mock_redis.type.return_value = "none"

        with patch.object(initializer._service_name_extractor, "extract_service_name", return_value="service1"):
            await initializer.initialize_from_existing_keys()

            mock_redis.zcard.assert_called()

    @pytest.mark.asyncio
    async def test_ensure_hash_history_key_exception(self, initializer, mock_redis):
        mock_redis.keys.return_value = ["history:service1"]
        mock_redis.type.side_effect = Exception("Redis error")

        with patch.object(initializer._service_name_extractor, "extract_service_name", return_value="service1"):
            await initializer.initialize_from_existing_keys()

            mock_redis.zcard.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_hlen_error(self, initializer, mock_redis, metadata_store):
        mock_redis.keys.return_value = ["history:service1"]
        mock_redis.zcard.side_effect = Exception("Count error")

        with patch.object(initializer._service_name_extractor, "extract_service_name", return_value="service1"):
            await initializer.initialize_from_existing_keys()

            metadata_store.initialize_service_count.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_hash_history_key_no_client(self, initializer):
        initializer.redis_client = None
        result = await initializer._ensure_sorted_set_history_key("key")
        assert result is False
