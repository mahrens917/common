import asyncio
from types import SimpleNamespace

import pytest
from redis.exceptions import RedisError

from common.exceptions import DataError
from common.redis_protocol.kalshi_store.cleaner import (
    KalshiMarketCleaner,
    _key_patterns,
    _metadata_patterns,
    _normalize_category_name,
)
from common.redis_protocol.kalshi_store.cleaner_helpers.market_remover import MarketRemover
from common.redis_protocol.kalshi_store.cleaner_helpers.metadata_cleaner import MetadataCleaner
from common.redis_protocol.kalshi_store.cleaner_helpers.pipeline_executor import (
    PipelineExecutor,
)
from common.redis_protocol.kalshi_store.cleanup_delegator import CleanupDelegator
from common.redis_schema.markets import KalshiMarketCategory


class _FakePipeline:
    def __init__(self) -> None:
        self.commands = []
        self.executed = False

    def srem(self, *args) -> None:
        self.commands.append(("srem",) + args)

    def hdel(self, *args) -> None:
        self.commands.append(("hdel",) + args)

    def delete(self, *args) -> None:
        self.commands.append(("delete",) + args)

    async def execute(self) -> None:
        self.executed = True


class _FailingPipeline(_FakePipeline):
    def __init__(self) -> None:
        super().__init__()
        self.raise_error = False

    async def execute(self) -> None:
        self.executed = True
        if self.raise_error:
            raise RedisError("fail")


class _FakeRedis:
    def __init__(self, keys=None, scan_results=None) -> None:
        self._keys = keys or []
        self._scan_results = scan_results or []
        self.deleted = []

    def pipeline(self) -> _FakePipeline:
        return _FakePipeline()

    async def keys(self, pattern):
        return list(self._keys)

    async def delete(self, *keys):
        self.deleted.extend(keys)
        return len(keys)

    def _iter_scan(self, results):
        for chunk in results:
            yield from chunk

    async def scan_iter(self, match=None, count=None):
        for key in self._iter_scan(self._scan_results):
            yield key


class _FakeConnectionManager:
    def __init__(self, redis):
        self.redis = redis
        self.ensure_calls = 0

    async def ensure_redis_connection(self) -> bool:
        self.ensure_calls += 1
        return True

    async def get_redis(self):
        return self.redis


@pytest.mark.asyncio
async def test_normalize_category_name_validation():
    assert _normalize_category_name(KalshiMarketCategory.BINARY) == "binary"
    assert _normalize_category_name(" BINARY ") == "binary"
    with pytest.raises(ValueError):
        _normalize_category_name("")
    with pytest.raises(ValueError):
        _normalize_category_name("unknown")


def test_metadata_and_key_patterns():
    assert _metadata_patterns(None, "default") == ["default"]
    assert _metadata_patterns([None], "default") == ["default"]
    assert _metadata_patterns(["binary"], "default") == ["markets:kalshi:binary:*"]

    # Order should retain base patterns then analytics (deduplicated)
    base_only = _key_patterns(["binary"], exclude_analytics=True)
    assert base_only == ["kalshi:binary:*", "markets:kalshi:binary:*"]

    with_analytics = _key_patterns(["binary"], exclude_analytics=False)
    assert with_analytics[-1] == "analytics:kalshi:binary:*"
    assert with_analytics[:2] == ["kalshi:binary:*", "markets:kalshi:binary:*"]


@pytest.mark.asyncio
async def test_pipeline_executor_handles_errors():
    pipe = _FailingPipeline()
    result = await PipelineExecutor.execute_pipeline(pipe, "success")
    assert result is True

    pipe = _FailingPipeline()
    pipe.raise_error = True
    result = await PipelineExecutor.execute_pipeline(pipe, "failure")
    assert result is False


@pytest.mark.asyncio
async def test_metadata_cleaner_batches_and_logs(caplog):
    redis = _FakeRedis(scan_results=[[b"one", "two"], ["three"]])

    async def get_redis():
        return redis

    cleaner = MetadataCleaner(get_redis)

    removed = await cleaner.clear_market_metadata("pattern:*", chunk_size=2)
    assert removed == 3
    assert redis.deleted == [b"one", "two", "three"]
    # second pass with no matches triggers debug path
    redis.deleted.clear()
    redis._scan_results = []
    with caplog.at_level("DEBUG"):
        removed = await cleaner.clear_market_metadata("pattern:*", chunk_size=2)
    assert removed == 0
    assert "No Kalshi market metadata keys matched" in caplog.text

    with pytest.raises(TypeError):
        await cleaner.clear_market_metadata(chunk_size=0)


@pytest.mark.asyncio
async def test_market_remover_remove_market_and_all_keys(monkeypatch):
    pipe = _FakePipeline()
    redis = _FakeRedis(keys=[b"kalshi:abc", "markets:kalshi:def"])
    redis.pipeline = lambda: pipe

    async def get_redis():
        return redis

    remover = MarketRemover(
        get_redis,
        subscriptions_key="subs",
        subscribed_markets_key="subscribed",
        service_prefix="ws",
        get_market_key_callback=lambda ticker: f"market:{ticker}",
        snapshot_key_callback=lambda ticker: f"snap:{ticker}",
    )

    executed_ops = []

    async def fake_execute(pipeline, operation_name):
        executed_ops.append((operation_name, list(pipeline.commands)))
        return True

    monkeypatch.setattr(PipelineExecutor, "execute_pipeline", fake_execute)
    assert await remover.remove_market_completely("ABC") is True
    assert executed_ops[0][0] == "remove market ABC"

    executed_ops.clear()
    assert await remover.remove_all_kalshi_keys(patterns=["kalshi:*", "markets:kalshi:*"]) is True
    op_name, commands = executed_ops[0]
    assert op_name == "remove all Kalshi keys"
    assert ("delete", "kalshi:abc") in commands
    assert ("delete", "markets:kalshi:def") in commands


@pytest.mark.asyncio
async def test_kalshi_market_cleaner_branches(monkeypatch):
    redis = _FakeRedis()
    connection_manager = _FakeConnectionManager(redis)
    cleaner = KalshiMarketCleaner(connection_manager=connection_manager)

    # Simulate missing connection path
    async def fail_connection():
        return False

    cleaner._ensure_redis_connection = fail_connection
    assert await cleaner.remove_market_completely("ABC") is False
    assert await cleaner.remove_service_keys() is False
    with pytest.raises(DataError):
        await cleaner.clear_market_metadata()

    # Success paths use the connection manager
    cleaner._ensure_redis_connection = connection_manager.ensure_redis_connection
    called = {}

    async def fake_remove_all(patterns=None):
        called["patterns"] = patterns
        return True

    cleaner._market_remover.remove_all_kalshi_keys = fake_remove_all
    assert await cleaner.remove_all_kalshi_keys(categories=["binary"], exclude_analytics=False)
    assert called["patterns"] == [
        "kalshi:binary:*",
        "markets:kalshi:binary:*",
        "analytics:kalshi:binary:*",
    ]


@pytest.mark.asyncio
async def test_cleanup_delegator_uses_cleaner(monkeypatch):
    calls = []

    class _FakeCleaner:
        async def remove_market_completely(self, ticker, category=None):
            calls.append(("remove", ticker, category))
            return True

        async def clear_market_metadata(self, pattern, chunk_size=500, categories=None):
            calls.append(("clear", pattern, chunk_size, categories))
            return 2

        async def remove_all_kalshi_keys(self, categories=None, exclude_analytics=True):
            calls.append(("remove_all", categories, exclude_analytics))
            return True

    delegator = CleanupDelegator(_FakeCleaner())
    assert await delegator.remove_market_completely("TCKR", category="crypto") is True
    assert await delegator.clear_market_metadata(chunk_size=10, categories=["crypto"]) == 2
    assert await delegator.remove_all_kalshi_keys(categories=["crypto"], exclude_analytics=False) is True

    assert calls[0] == ("remove", "TCKR", "crypto")
    assert calls[1] == ("clear", "markets:kalshi:*", 10, ["crypto"])
    assert calls[2] == ("remove_all", ["crypto"], False)
