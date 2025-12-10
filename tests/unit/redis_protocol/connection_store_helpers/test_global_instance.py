from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.redis_protocol.connection_store_helpers import global_instance
from common.redis_protocol.connection_store_helpers.global_instance import get_connection_store


class TestGlobalInstance:
    def setup_method(self):
        global_instance._connection_store = None

    def teardown_method(self):
        global_instance._connection_store = None

    @pytest.mark.asyncio
    async def test_get_connection_store_initializes_once(self):
        with patch("common.redis_protocol.connection_store.ConnectionStore") as MockStore:
            instance = AsyncMock()
            MockStore.return_value = instance

            store1 = await get_connection_store()
            store2 = await get_connection_store()

            assert store1 is instance
            assert store2 is instance
            assert MockStore.call_count == 1
            instance.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_connection_store_returns_existing(self):
        existing = MagicMock()
        global_instance._connection_store = existing

        store = await get_connection_store()
        assert store is existing
