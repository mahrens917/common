import logging
from typing import Any, Dict, List, Set
from unittest.mock import AsyncMock

import pytest

from common.dependency_aware_error_filter import (
    DependencyAwareErrorFilter,
    ErrorSuppressionConfig,
)


class FakeRedis:
    def __init__(self):
        self.sets: Dict[str, Set[Any]] = {}
        self.hashes: Dict[str, Dict[str, Any]] = {}
        self.deleted: List[str] = []
        self.close_calls = 0

    async def smembers(self, key: str):
        return self.sets.get(key, set())

    async def sadd(self, key: str, *members: Any):
        self.sets.setdefault(key, set()).update(members)

    async def delete(self, key: str):
        self.deleted.append(key)
        self.sets.pop(key, None)

    async def hget(self, key: str, field: str):
        return self.hashes.get(key, {}).get(field)

    async def hset(self, key: str, field: str, value: Any):
        self.hashes.setdefault(key, {})[field] = value

    async def close(self):
        self.close_calls += 1

    async def aclose(self):
        await self.close()


@pytest.mark.asyncio
async def test_should_suppress_error_when_dependency_unavailable():
    config = ErrorSuppressionConfig(
        dependency_error_patterns={"redis": [r"timeout", r"connection lost"]}
    )
    filter_ = DependencyAwareErrorFilter(config)
    fake_redis = FakeRedis()
    fake_redis.sets["service_dependencies:worker"] = {"redis"}
    fake_redis.hashes["dependency_status:worker"] = {"redis": "unavailable"}
    filter_.redis = fake_redis  # bypass context manager setup

    suppress = await filter_.should_suppress_error("worker", "Redis timeout error")
    assert suppress is True


@pytest.mark.asyncio
async def test_should_not_suppress_when_disabled(monkeypatch):
    config = ErrorSuppressionConfig(enabled=False)
    filter_ = DependencyAwareErrorFilter(config)
    filter_.redis = FakeRedis()
    result = await filter_.should_suppress_error("svc", "dependency issue")
    assert result is False


def test_invalid_regex_patterns_skipped(caplog):
    config = ErrorSuppressionConfig(dependency_error_patterns={"svc": [r"[unbalanced"]})
    filter_ = DependencyAwareErrorFilter(config)
    assert filter_.dependency_patterns["svc"].compiled_patterns == []
    assert any("Invalid regex pattern" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_dependency_helpers_update_redis():
    config = ErrorSuppressionConfig(dependency_error_patterns={"svc": [r"error"]})
    filter_ = DependencyAwareErrorFilter(config)
    fake_redis = FakeRedis()
    filter_.redis = fake_redis

    await filter_.update_service_dependencies("svc", ["db", "cache"])
    assert "service_dependencies:svc" in fake_redis.deleted
    assert fake_redis.sets["service_dependencies:svc"] == {"db", "cache"}
    await filter_.update_dependency_status("svc", "db", "unavailable")
    assert fake_redis.hashes["dependency_status:svc"]["db"] == "unavailable"

    # bytes responses from redis should be decoded
    fake_redis.sets["service_dependencies:svc"] = {b"db"}
    fake_redis.hashes["dependency_status:svc"] = {"db": b"unknown"}
    suppress = await filter_.should_suppress_error("svc", "DB connection error")
    assert suppress is False  # no matching pattern configured


@pytest.mark.asyncio
async def test_context_manager_manages_redis_connection(monkeypatch):
    config = ErrorSuppressionConfig(dependency_error_patterns={})
    filter_ = DependencyAwareErrorFilter(config)
    fake_redis = FakeRedis()

    async def fake_get_connection():
        return fake_redis

    monkeypatch.setattr(
        "common.dependency_aware_error_filter.get_redis_connection",
        fake_get_connection,
    )

    async with filter_ as active_filter:
        assert active_filter.redis is fake_redis
    assert fake_redis.close_calls == 1


@pytest.mark.asyncio
async def test_context_manager_logs_when_exiting_due_to_error(monkeypatch, caplog):
    config = ErrorSuppressionConfig()
    filter_ = DependencyAwareErrorFilter(config)
    fake_redis = FakeRedis()

    async def fake_get_connection():
        return fake_redis

    monkeypatch.setattr(
        "common.dependency_aware_error_filter.get_redis_connection",
        fake_get_connection,
    )

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(RuntimeError):
            async with filter_:
                raise RuntimeError("boom")
    assert fake_redis.close_calls == 1
    assert any(
        "DependencyAwareErrorFilter closing due to RuntimeError" in r.message
        for r in caplog.records
    )


@pytest.mark.asyncio
async def test_should_suppress_error_handles_internal_failures():
    config = ErrorSuppressionConfig(dependency_error_patterns={"svc": [r"error"]})
    filter_ = DependencyAwareErrorFilter(config)
    filter_.redis = FakeRedis()
    filter_._get_service_dependencies = AsyncMock(side_effect=RuntimeError("redis down"))  # type: ignore[assignment]

    result = await filter_.should_suppress_error("svc", "dependency failure")
    assert result is False


@pytest.mark.asyncio
async def test_is_dependency_unavailable_handles_status_variants():
    config = ErrorSuppressionConfig(dependency_error_patterns={})
    filter_ = DependencyAwareErrorFilter(config)
    fake_redis = FakeRedis()
    filter_.redis = fake_redis

    fake_redis.hashes["dependency_status:svc"] = {"db": "Unknown"}
    assert await filter_._is_dependency_unavailable("svc", "db") is True

    fake_redis.hashes["dependency_status:svc"]["db"] = "available"
    assert await filter_._is_dependency_unavailable("svc", "db") is False

    fake_redis.hashes["dependency_status:svc"]["db"] = None  # type: ignore[assignment]
    assert await filter_._is_dependency_unavailable("svc", "db") is False


@pytest.mark.asyncio
async def test_is_dependency_unavailable_without_redis_returns_false(caplog):
    config = ErrorSuppressionConfig(dependency_error_patterns={})
    filter_ = DependencyAwareErrorFilter(config)

    with caplog.at_level(logging.WARNING):
        assert await filter_._is_dependency_unavailable("svc", "db") is False
    assert any("dependency status check" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_get_service_dependencies_decodes_bytes():
    config = ErrorSuppressionConfig()
    filter_ = DependencyAwareErrorFilter(config)
    fake_redis = FakeRedis()
    fake_redis.sets["service_dependencies:svc"] = {b"db", "cache"}
    filter_.redis = fake_redis

    dependencies = await filter_._get_service_dependencies("svc")
    assert sorted(dependencies) == ["cache", "db"]


def test_dependency_related_error_handles_pattern_failures(caplog):
    config = ErrorSuppressionConfig(dependency_error_patterns={"svc": [r"matched"]})
    filter_ = DependencyAwareErrorFilter(config)
    pattern_config = filter_.dependency_patterns["svc"]

    class BrokenPattern:
        pattern = "broken"

        def search(self, message: str):
            raise RuntimeError("pattern fail")

    pattern_config.compiled_patterns.insert(0, BrokenPattern())  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="pattern fail"):
        filter_._is_dependency_related_error("thing matched", "svc")


@pytest.mark.asyncio
async def test_update_service_dependencies_without_items_clears_set():
    config = ErrorSuppressionConfig()
    filter_ = DependencyAwareErrorFilter(config)
    fake_redis = FakeRedis()
    filter_.redis = fake_redis
    fake_redis.sets["service_dependencies:svc"] = {"existing"}

    await filter_.update_service_dependencies("svc", [])
    assert "service_dependencies:svc" in fake_redis.deleted
    assert "service_dependencies:svc" not in fake_redis.sets


@pytest.mark.asyncio
async def test_update_dependency_status_without_redis_logs_warning(caplog):
    config = ErrorSuppressionConfig()
    filter_ = DependencyAwareErrorFilter(config)

    with caplog.at_level(logging.WARNING):
        await filter_.update_dependency_status("svc", "db", "unavailable")
    assert any(
        "No Redis connection available for updating dependency status" in record.message
        for record in caplog.records
    )
