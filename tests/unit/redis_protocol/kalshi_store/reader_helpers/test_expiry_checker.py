import logging
from datetime import datetime, timedelta, timezone

import pytest

from src.common.redis_protocol.kalshi_store.reader_helpers import expiry_checker


class _DummyRedis:
    def __init__(self, data):
        self._data = data

    async def hgetall(self, key):
        return self._data


@pytest.mark.asyncio
async def test_is_market_expired_logs_and_returns_true(monkeypatch):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        "src.common.redis_protocol.kalshi_store.reader_helpers.expiry_checker.get_current_utc",
        lambda: now,
    )
    monkeypatch.setattr(
        "src.common.redis_protocol.kalshi_store.reader_helpers.expiry_checker.CloseTimeParser.decode_close_time_string",
        lambda raw: raw.decode("utf-8") if isinstance(raw, bytes) else raw,
    )
    monkeypatch.setattr(
        "src.common.redis_protocol.kalshi_store.reader_helpers.expiry_checker.CloseTimeParser.parse_close_time_from_field",
        lambda raw: now - timedelta(minutes=1),
    )
    redis = _DummyRedis({"close_time": "old"})
    checker = expiry_checker.ExpiryChecker(logger_instance=logging.getLogger("tests"))
    result = await expiry_checker.ExpiryChecker.is_market_expired(checker, redis, "key", "ticker")
    assert result is True


@pytest.mark.asyncio
async def test_is_market_settled_handles_future(monkeypatch):
    now = datetime.now(timezone.utc)
    future = now + timedelta(minutes=5)
    monkeypatch.setattr(
        "src.common.redis_protocol.kalshi_store.reader_helpers.expiry_checker.get_current_utc",
        lambda: now,
    )
    monkeypatch.setattr(
        "src.common.redis_protocol.kalshi_store.reader_helpers.expiry_checker.CloseTimeParser.decode_close_time_string",
        lambda raw: raw.decode("utf-8") if isinstance(raw, bytes) else raw,
    )
    redis = _DummyRedis({"close_time": future.isoformat()})
    checker = expiry_checker.ExpiryChecker(logger_instance=logging.getLogger("tests"))
    result = await expiry_checker.ExpiryChecker.is_market_settled(checker, redis, "key", "ticker")
    assert result is False


@pytest.mark.asyncio
async def test_is_market_expired_handles_empty(monkeypatch):
    checker = expiry_checker.ExpiryChecker(logger_instance=logging.getLogger("tests"))
    result = await expiry_checker.ExpiryChecker.is_market_expired(
        checker, _DummyRedis({}), "key", "ticker"
    )
    assert result is False


@pytest.mark.asyncio
async def test_is_market_expired_logs_errors(monkeypatch):
    class BrokenRedis(_DummyRedis):
        async def hgetall(self, key):
            raise expiry_checker.REDIS_ERRORS[0]("boom")

    checker = expiry_checker.ExpiryChecker(logger_instance=logging.getLogger("tests"))
    result = await expiry_checker.ExpiryChecker.is_market_expired(
        checker, BrokenRedis({}), "key", "ticker"
    )
    assert result is False


@pytest.mark.asyncio
async def test_is_market_settled_handles_missing_close(monkeypatch):
    checker = expiry_checker.ExpiryChecker(logger_instance=logging.getLogger("tests"))
    monkeypatch.setattr(
        "src.common.redis_protocol.kalshi_store.reader_helpers.expiry_checker.CloseTimeParser.decode_close_time_string",
        lambda raw: "",
    )
    result = await expiry_checker.ExpiryChecker.is_market_settled(
        checker, _DummyRedis({"close_time": None}), "key", "ticker"
    )
    assert result is False


@pytest.mark.asyncio
async def test_is_market_expired_returns_false_when_not_expired(monkeypatch):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        "src.common.redis_protocol.kalshi_store.reader_helpers.expiry_checker.get_current_utc",
        lambda: now,
    )
    monkeypatch.setattr(
        "src.common.redis_protocol.kalshi_store.reader_helpers.expiry_checker.CloseTimeParser.parse_close_time_from_field",
        lambda raw: None,
    )
    result = await expiry_checker.ExpiryChecker.is_market_expired(
        expiry_checker.ExpiryChecker(logger_instance=logging.getLogger("tests")),
        _DummyRedis({"close_time": "now"}),
        "key",
        "ticker",
    )
    assert result is False


@pytest.mark.asyncio
async def test_is_market_settled_handles_redis_error(monkeypatch):
    class BrokenRedis(_DummyRedis):
        async def hgetall(self, key):
            raise expiry_checker.REDIS_ERRORS[0]("boom")

    checker = expiry_checker.ExpiryChecker(logger_instance=logging.getLogger("tests"))
    result = await expiry_checker.ExpiryChecker.is_market_settled(
        checker, BrokenRedis({"close_time": "now"}), "key", "ticker"
    )
    assert result is False
