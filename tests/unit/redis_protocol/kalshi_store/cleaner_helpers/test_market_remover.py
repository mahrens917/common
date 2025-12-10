import asyncio

import pytest

from common.redis_protocol.kalshi_store.cleaner_helpers import market_remover, pipeline_executor


class _DummyPipeline:
    def __init__(self):
        self.commands = []

    def srem(self, *args, **kwargs):
        self.commands.append("srem")

    def hdel(self, *args, **kwargs):
        self.commands.append("hdel")

    def delete(self, *args):
        self.commands.append("delete")

    async def execute(self):
        return True


class _DummyRedis:
    def __init__(self, keys=None):
        self._keys = keys or []

    def pipeline(self):
        return _DummyPipeline()

    async def keys(self, pattern):
        return self._keys


class _DummyGetter:
    def __init__(self, redis):
        self.redis = redis

    async def __call__(self):
        return self.redis


@pytest.mark.asyncio
async def test_remove_market_completely_success(monkeypatch):
    redis = _DummyRedis()
    remover = market_remover.MarketRemover(
        redis_getter=_DummyGetter(redis),
        subscriptions_key="subs",
        subscribed_markets_key="subs_set",
        service_prefix="ws",
        get_market_key_callback=lambda ticker: "key:" + ticker,
        snapshot_key_callback=lambda ticker: "snap:" + ticker,
    )

    async def execute_pipeline(cls, pipe, op):
        return True

    async def execute_pipeline(cls, pipe, op):
        return True

    monkeypatch.setattr(
        pipeline_executor.PipelineExecutor,
        "execute_pipeline",
        classmethod(execute_pipeline),
    )
    result = await market_remover.MarketRemover.remove_market_completely(remover, b"TK1")
    assert result is True


@pytest.mark.asyncio
async def test_remove_all_kalshi_keys_handles_empty(monkeypatch):
    redis = _DummyRedis()
    remover = market_remover.MarketRemover(
        redis_getter=_DummyGetter(redis),
        subscriptions_key="subs",
        subscribed_markets_key="subs_set",
        service_prefix="ws",
        get_market_key_callback=lambda ticker: "key:" + ticker,
    )

    async def execute_pipeline(cls, pipe, op):
        return True

    monkeypatch.setattr(
        pipeline_executor.PipelineExecutor,
        "execute_pipeline",
        classmethod(execute_pipeline),
    )
    assert await market_remover.MarketRemover.remove_all_kalshi_keys(remover) is True


@pytest.mark.asyncio
async def test_remove_all_kalshi_keys_with_entries(monkeypatch):
    redis = _DummyRedis(keys=["key1", b"key2"])
    remover = market_remover.MarketRemover(
        redis_getter=_DummyGetter(redis),
        subscriptions_key="subs",
        subscribed_markets_key="subs_set",
        service_prefix="ws",
        get_market_key_callback=lambda ticker: "key:" + ticker,
    )
    redis.hgetall = lambda key: {}

    async def fake_keys(pattern):
        return ["key1"]

    async def fake_keys(pattern):
        return ["key1"]

    redis.keys = fake_keys

    class _Pipe:
        def delete(self, *args):
            pass

        async def execute(self):
            return True

    redis.pipeline = lambda: _Pipe()

    async def execute_pipeline(cls, pipe, op):
        return True

    monkeypatch.setattr(
        pipeline_executor.PipelineExecutor,
        "execute_pipeline",
        classmethod(execute_pipeline),
    )

    assert await market_remover.MarketRemover.remove_all_kalshi_keys(remover, patterns=["pattern"])
