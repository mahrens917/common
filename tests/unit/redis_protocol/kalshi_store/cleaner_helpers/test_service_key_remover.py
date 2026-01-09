import pytest

from common.redis_protocol.kalshi_store.cleaner_helpers.service_key_remover import (
    ServiceKeyRemover,
)


class _DummyRedis:
    def __init__(self, keys=None, subs=None):
        self.keys_values = keys or []
        self.subscriptions = subs or {}
        self.calls = []
        self.deleted_keys = []

    async def keys(self, pattern):
        return self.keys_values

    async def hgetall(self, key):
        return self.subscriptions

    async def delete(self, key):
        self.deleted_keys.append(key)
        return 1

    def pipeline(self):
        class _Pipe:
            def __init__(self, calls):
                self.calls = calls

            def delete(self, *args):
                self.calls.append(("delete", args))

            def hdel(self, key, field):
                self.calls.append(("hdel", key, field))

            async def execute(self):
                return True

        return _Pipe(self.calls)


class _DummyGetter:
    def __init__(self, redis):
        self.redis = redis

    async def __call__(self):
        return self.redis


@pytest.mark.asyncio
async def test_remove_service_keys_skips_when_empty():
    redis = _DummyRedis(keys=[], subs={})
    remover = ServiceKeyRemover(_DummyGetter(redis), "subs", "ws", "kalshi:subscription_ids:ws")
    assert await remover.remove_service_keys() is True
    assert "kalshi:subscription_ids:ws" in redis.deleted_keys


@pytest.mark.asyncio
async def test_remove_service_keys_deletes_entries():
    redis = _DummyRedis(keys=["kalshi:ws:key"], subs={b"ws:TK": b"1"})
    remover = ServiceKeyRemover(_DummyGetter(redis), "subs", "ws", "kalshi:subscription_ids:ws")
    assert await remover.remove_service_keys() is True
    assert any(call[0] == "delete" for call in redis.calls)
    assert "kalshi:subscription_ids:ws" in redis.deleted_keys
