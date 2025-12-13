from __future__ import annotations

import pytest

from common.redis_protocol.kalshi_store.writer_helpers.market_update_writer import RedisConnectionMixin


@pytest.mark.asyncio
async def test_ensure_redis_uses_connection_manager_and_caches_client():
    sentinel = object()

    class DummyConnectionManager:
        async def get_redis(self):
            return sentinel

    class DummyWriter(RedisConnectionMixin):
        def __init__(self):
            self.redis = None
            self._connection_manager = DummyConnectionManager()

    writer = DummyWriter()
    redis = await writer._ensure_redis()

    assert redis is sentinel
    assert writer.redis is sentinel
