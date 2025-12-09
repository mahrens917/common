import logging
import re
from unittest.mock import AsyncMock

import pytest

from src.common.dependency_aware_error_filter_helpers.dependency_checker import DependencyChecker
from src.common.dependency_aware_error_filter_helpers.pattern_matcher import (
    DependencyErrorPattern,
    PatternMatcher,
)
from src.common.dependency_aware_error_filter_helpers.status_updater import StatusUpdater

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_get_service_dependencies_decodes_bytes():
    redis = AsyncMock()
    redis.smembers.return_value = [b"alpha", "beta"]

    dependencies = await DependencyChecker.get_service_dependencies(redis, "svc-name")

    assert dependencies == ["alpha", "beta"]
    redis.smembers.assert_awaited_with("service_dependencies:svc-name")


@pytest.mark.asyncio
async def test_get_service_dependencies_handles_connection_errors(caplog):
    caplog.set_level(logging.ERROR)
    redis = AsyncMock()
    redis.smembers.side_effect = ConnectionError("boom")

    dependencies = await DependencyChecker.get_service_dependencies(redis, "svc-name")

    assert dependencies == []
    assert "Failed to get dependencies for" in caplog.text


@pytest.mark.asyncio
async def test_is_dependency_unavailable_detects_status():
    redis = AsyncMock()
    redis.hget.return_value = b"Unavailable"

    unavailable = await DependencyChecker.is_dependency_unavailable(redis, "svc", "db", "status")

    assert unavailable is True
    redis.hget.assert_awaited_with("status:svc", "db")


@pytest.mark.asyncio
async def test_is_dependency_unavailable_handles_none_and_errors(caplog):
    caplog.set_level(logging.ERROR)
    redis = AsyncMock()
    redis.hget.return_value = None

    assert (
        await DependencyChecker.is_dependency_unavailable(redis, "svc", "cache", "status") is False
    )

    redis.hget.side_effect = OSError("network")
    assert (
        await DependencyChecker.is_dependency_unavailable(redis, "svc", "cache", "status") is False
    )
    assert "Failed to check dependency status" in caplog.text


def test_dependency_error_pattern_compiles_and_logs_invalid_pattern(caplog):
    caplog.set_level(logging.ERROR)

    pattern = DependencyErrorPattern("db", ["timeout", "("])

    assert pattern.compiled_patterns is not None
    assert len(pattern.compiled_patterns) == 1
    assert pattern.compiled_patterns[0].pattern == "timeout"
    assert "Invalid regex pattern" in caplog.text


def test_pattern_matcher_matches_and_handles_search_errors(caplog):
    caplog.set_level(logging.WARNING)

    class BadPattern:
        pattern = "bad"

        def search(self, message: str):
            raise re.error("bad pattern")

    pattern_config = DependencyErrorPattern("db", ["ok"])
    # Overwrite with a mix of failing and working compiled patterns
    pattern_config.compiled_patterns = [BadPattern(), re.compile("failure", re.IGNORECASE)]

    dependency_patterns = {"db": pattern_config}
    assert PatternMatcher.is_dependency_related_error(
        "query FAILURE due to timeout", "db", dependency_patterns
    )
    assert "Error matching pattern bad" in caplog.text


@pytest.mark.asyncio
async def test_update_service_dependencies_sets_members():
    redis = AsyncMock()

    await StatusUpdater.update_service_dependencies(redis, "svc", ["a", "b"])

    redis.delete.assert_awaited_with("service_dependencies:svc")
    redis.sadd.assert_awaited_with("service_dependencies:svc", "a", "b")


@pytest.mark.asyncio
async def test_update_service_dependencies_swallows_errors(caplog):
    caplog.set_level(logging.ERROR)
    redis = AsyncMock()
    redis.delete.side_effect = RuntimeError("boom")

    await StatusUpdater.update_service_dependencies(redis, "svc", ["a"])

    assert "Failed to update dependencies" in caplog.text


@pytest.mark.asyncio
async def test_update_dependency_status_sets_hash_and_handles_error(caplog):
    redis = AsyncMock()

    await StatusUpdater.update_dependency_status(redis, "svc", "db", "unavailable", "status")
    redis.hset.assert_awaited_with("status:svc", "db", "unavailable")

    caplog.set_level(logging.ERROR)
    redis.hset.side_effect = ConnectionError("oops")
    await StatusUpdater.update_dependency_status(redis, "svc", "db", "ok", "status")
    assert "Failed to update dependency status" in caplog.text
