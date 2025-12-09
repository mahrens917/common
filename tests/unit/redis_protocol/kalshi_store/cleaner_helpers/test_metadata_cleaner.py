import asyncio

import pytest

from src.common.redis_protocol.kalshi_store.cleaner_helpers.metadata_cleaner import (
    MetadataCleaner,
)


class _DummyRedis:
    def __init__(self, keys):
        self.keys = keys

    async def scan_iter(self, match, count):
        for key in self.keys:
            yield key

    async def delete(self, *keys):
        return len(keys)


class _DummyGetter:
    def __init__(self, redis):
        self.redis = redis

    async def __call__(self):
        return self.redis


@pytest.mark.asyncio
async def test_clear_market_metadata_counts_deletions():
    redis = _DummyRedis(["key1", "key2"])
    cleaner = MetadataCleaner(_DummyGetter(redis))
    total = await cleaner.clear_market_metadata(pattern="pattern", chunk_size=1)
    assert total == 2


@pytest.mark.asyncio
async def test_clear_market_metadata_invalid_chunk():
    redis = _DummyRedis([])
    cleaner = MetadataCleaner(_DummyGetter(redis))
    with pytest.raises(TypeError):
        await cleaner.clear_market_metadata(chunk_size=0)
