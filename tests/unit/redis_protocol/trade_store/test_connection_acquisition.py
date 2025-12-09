"""Tests for TradeStore connection acquisition helper."""

import asyncio

import pytest

from src.common.redis_protocol.trade_store.errors import TradeStoreError
from src.common.redis_protocol.trade_store.store_helpers.connection_manager_helpers.acquisition import (
    ConnectionAcquisitionHelper,
)


class DummyConnection:
    def __init__(self):
        self.initialized = False


class DummyLogger:
    def __init__(self):
        self.messages = []

    def warning(self, msg, *args):
        self.messages.append(msg % args if args else msg)


class DummyRedis:
    pass


@pytest.mark.asyncio
async def test_acquisition_success_after_reconnect():
    logger = DummyLogger()
    connection = DummyConnection()
    helper = ConnectionAcquisitionHelper(logger, connection)

    redis_instance = DummyRedis()

    def redis_getter():
        return redis_instance if connection.initialized else None

    async def ensure_conn():
        connection.initialized = True
        return True

    async def ping(client):
        return True, False

    redis = await helper.get_redis(redis_getter, ensure_conn, ping)
    assert redis is redis_instance
    assert connection.initialized


@pytest.mark.asyncio
async def test_acquisition_fails_when_ping_cannot_recover():
    logger = DummyLogger()
    connection = DummyConnection()
    helper = ConnectionAcquisitionHelper(logger, connection)

    def redis_getter():
        return None

    async def ensure_conn():
        return False

    async def ping(_client):
        return False, True

    with pytest.raises(TradeStoreError):
        await helper.get_redis(redis_getter, ensure_conn, ping)
