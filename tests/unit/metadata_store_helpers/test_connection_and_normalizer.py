import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.metadata_store_helpers.connection_manager import ConnectionManager
from src.common.metadata_store_helpers.data_normalizer import DataNormalizer


class TestConnectionManager(unittest.IsolatedAsyncioTestCase):
    async def test_initialize_and_get_client(self):
        manager = ConnectionManager()
        with patch(
            "src.common.metadata_store_helpers.connection_manager.get_redis_connection",
            new_callable=AsyncMock,
        ) as mock_get_conn:
            mock_client = AsyncMock()
            mock_get_conn.return_value = mock_client

            client = await manager.get_client()
            assert client == mock_client
            assert manager.redis_client == mock_client
            mock_get_conn.assert_called_once()

            # Second call should use existing client
            client2 = await manager.get_client()
            assert client2 == mock_client
            mock_get_conn.assert_called_once()

    async def test_get_client_fails(self):
        manager = ConnectionManager()
        with patch(
            "src.common.metadata_store_helpers.connection_manager.get_redis_connection",
            new_callable=AsyncMock,
        ) as mock_get_conn:
            mock_get_conn.return_value = None
            with pytest.raises(ConnectionError, match="Redis client not initialized"):
                await manager.get_client()

    async def test_cleanup(self):
        manager = ConnectionManager()
        mock_client = AsyncMock()
        manager.redis_client = mock_client

        await manager.cleanup()
        mock_client.aclose.assert_called_once()
        assert manager.redis_client is None

        # Cleanup when no client
        await manager.cleanup()  # Should not raise error


class TestDataNormalizer(unittest.TestCase):
    def test_normalize_hash(self):
        raw = {b"key1": b"value1", "key2": "value2", b"key3": 123}
        expected = {"key1": "value1", "key2": "value2", "key3": 123}
        assert DataNormalizer.normalize_hash(raw) == expected

    def test_int_field(self):
        data = {"a": 1, "b": "2", "c": " 3.5 ", "d": True, "e": None, "f": ""}
        assert DataNormalizer.int_field(data, "a") == 1
        assert DataNormalizer.int_field(data, "b") == 2
        assert DataNormalizer.int_field(data, "c") == 3
        assert DataNormalizer.int_field(data, "d") == 1
        assert DataNormalizer.int_field(data, "e", default=10) == 10
        assert DataNormalizer.int_field(data, "f", default=5) == 5
        assert DataNormalizer.int_field(data, "missing", default=99) == 99

        with pytest.raises(ValueError):
            DataNormalizer.int_field({"x": "invalid"}, "x")

    def test_float_field(self):
        data = {"a": 1.5, "b": "2.5", "c": " 3 ", "d": True, "e": None, "f": ""}
        assert DataNormalizer.float_field(data, "a") == 1.5
        assert DataNormalizer.float_field(data, "b") == 2.5
        assert DataNormalizer.float_field(data, "c") == 3.0
        assert DataNormalizer.float_field(data, "d") == 1.0
        assert DataNormalizer.float_field(data, "e", default=10.5) == 10.5
        assert DataNormalizer.float_field(data, "f", default=5.5) == 5.5
        assert DataNormalizer.float_field(data, "missing", default=99.9) == 99.9

        with pytest.raises(ValueError):
            DataNormalizer.float_field({"x": "invalid"}, "x")
