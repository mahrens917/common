from unittest.mock import AsyncMock

import pytest

from common.config.redis_schema import get_schema_config


@pytest.mark.asyncio
async def test_fake_redis_key_value_and_scan(fake_redis):
    await fake_redis.set("sample:key", "value")
    await fake_redis.incrby("counter", 2)

    assert await fake_redis.get("sample:key") == "value"
    assert await fake_redis.get("counter") == "2"

    keys = []
    async for key in fake_redis.scan_iter(match="sample:*"):
        keys.append(key)

    assert keys == ["sample:key"]


@pytest.mark.asyncio
async def test_fake_redis_hash_and_pipeline(fake_redis):
    pipe = fake_redis.pipeline()
    pipe.hset("hash:key", "field", "1")
    pipe.hincrby("hash:key", "field", 2)
    pipe.expire("hash:key", 300)
    results = await pipe.execute()

    assert results == [1, 3, True]
    assert fake_redis.dump_hash("hash:key") == {"field": "3"}

    async with fake_redis.pipeline() as transactional:
        transactional.hdel("hash:key", "field")
        await transactional.execute()

    assert fake_redis.dump_hash("hash:key") == {}


def test_stub_schema_config_exposes_overrides(stub_schema_config, schema_config_factory):
    default = get_schema_config()
    assert default is stub_schema_config
    assert default.kalshi_market_prefix == "markets:kalshi"

    custom = schema_config_factory(kalshi_market_prefix="markets:kalshi:custom")
    assert get_schema_config() is custom
    assert custom.kalshi_market_prefix == "markets:kalshi:custom"


@pytest.mark.asyncio
async def test_fake_redis_client_factory_patches(monkeypatch, fake_redis_client_factory):
    fake = fake_redis_client_factory("common.redis_protocol.connection.get_redis_pool")

    import redis.asyncio  # patched by fixture

    client = redis.asyncio.Redis()
    assert client is fake

    from common.redis_protocol import connection

    pool = await connection.get_redis_pool()
    assert isinstance(connection.get_redis_pool, AsyncMock)
    assert pool is connection.get_redis_pool.return_value
    assert connection.get_redis_pool.await_count == 1
