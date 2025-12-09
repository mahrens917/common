"""Tests for the Redis connection verifier helpers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.common.redis_protocol.kalshi_store.connection_helpers import connection_verifier


class DummyRedisError(Exception):
    pass


@pytest.mark.asyncio
async def test_ping_success(monkeypatch):
    redis = MagicMock()
    redis.ping = AsyncMock()
    wait_for = AsyncMock(return_value=None)
    monkeypatch.setattr(connection_verifier.asyncio, "wait_for", wait_for)

    success, fatal = await connection_verifier.ConnectionVerifier.ping_connection(redis)

    assert success is True
    assert fatal is False
    wait_for.assert_awaited_once()
    assert wait_for.await_args.kwargs["timeout"] == 5.0


@pytest.mark.asyncio
async def test_ping_handles_timeout(monkeypatch):
    redis = MagicMock()
    redis.ping = AsyncMock()

    async def _raise_timeout(*_, **__):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(connection_verifier.asyncio, "wait_for", _raise_timeout)

    success, fatal = await connection_verifier.ConnectionVerifier.ping_connection(
        redis, timeout=1.0
    )

    assert success is False
    assert fatal is False


@pytest.mark.asyncio
async def test_ping_handles_event_loop_closed(monkeypatch):
    redis = MagicMock()
    redis.ping = AsyncMock()
    monkeypatch.setattr(
        connection_verifier,
        "REDIS_ERRORS",
        (DummyRedisError,),
    )

    async def _raise_event_loop(*_, **__):
        raise DummyRedisError("Event loop is closed")

    monkeypatch.setattr(connection_verifier.asyncio, "wait_for", _raise_event_loop)

    success, fatal = await connection_verifier.ConnectionVerifier.ping_connection(redis)

    assert success is False
    assert fatal is True


@pytest.mark.asyncio
async def test_ping_handles_generic_redis_error(monkeypatch):
    redis = MagicMock()
    redis.ping = AsyncMock()
    monkeypatch.setattr(
        connection_verifier,
        "REDIS_ERRORS",
        (DummyRedisError,),
    )

    async def _raise_error(*_, **__):
        raise DummyRedisError("some other failure")

    monkeypatch.setattr(connection_verifier.asyncio, "wait_for", _raise_error)

    success, fatal = await connection_verifier.ConnectionVerifier.ping_connection(redis)

    assert success is False
    assert fatal is False


@pytest.mark.asyncio
async def test_attach_redis_client_validates(monkeypatch):
    redis_client = MagicMock()
    redis_client.ping = AsyncMock()
    wait_for = AsyncMock(return_value=None)
    monkeypatch.setattr(connection_verifier.asyncio, "wait_for", wait_for)

    await connection_verifier.ConnectionVerifier.attach_redis_client(redis_client)

    wait_for.assert_awaited_once()
    assert wait_for.await_args.kwargs["timeout"] == 5.0


@pytest.mark.asyncio
async def test_attach_redis_client_rejects_none():
    with pytest.raises(ValueError):
        await connection_verifier.ConnectionVerifier.attach_redis_client(None)


@pytest.mark.asyncio
async def test_attach_redis_client_requires_ping():
    class FakeRedis:
        pass

    with pytest.raises(ValueError):
        await connection_verifier.ConnectionVerifier.attach_redis_client(FakeRedis())


@pytest.mark.asyncio
async def test_attach_redis_client_handles_timeout(monkeypatch):
    redis_client = MagicMock()
    redis_client.ping = AsyncMock()

    async def _raise_timeout(*_, **__):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(connection_verifier.asyncio, "wait_for", _raise_timeout)

    with pytest.raises(RuntimeError):
        await connection_verifier.ConnectionVerifier.attach_redis_client(redis_client)


@pytest.mark.asyncio
async def test_attach_redis_client_handles_redis_error(monkeypatch):
    redis_client = MagicMock()
    redis_client.ping = AsyncMock()
    monkeypatch.setattr(
        connection_verifier,
        "REDIS_ERRORS",
        (DummyRedisError,),
    )

    async def _raise_error(*_, **__):
        raise DummyRedisError("broken")

    monkeypatch.setattr(connection_verifier.asyncio, "wait_for", _raise_error)

    with pytest.raises(RuntimeError):
        await connection_verifier.ConnectionVerifier.attach_redis_client(redis_client)


@pytest.mark.asyncio
async def test_ping_returns_success_when_ping_missing():
    class PartialRedis:
        pass

    partial = PartialRedis()

    success, fatal = await connection_verifier.ConnectionVerifier.ping_connection(partial)

    assert success is True
    assert fatal is False


@pytest.mark.asyncio
async def test_verify_connection_delegates_to_ping(monkeypatch):
    redis = MagicMock()
    ping_mock = AsyncMock(return_value=(True, False))
    monkeypatch.setattr(connection_verifier.ConnectionVerifier, "ping_connection", ping_mock)

    result = await connection_verifier.ConnectionVerifier.verify_connection(redis)

    assert result == (True, False)
    ping_mock.assert_awaited_once_with(redis)
