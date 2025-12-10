import pytest

from common.redis_protocol.retry import RedisFatalError
from common.redis_protocol.trade_store.errors import TradeStoreError
from common.redis_protocol.trade_store.store_helpers.connection_manager_helpers.acquisition import (
    ConnectionAcquisitionHelper,
)
from common.redis_protocol.trade_store.store_helpers.connection_manager_helpers.retry_helpers.operation_factory import (
    ConnectionOperationConfig,
    create_connection_operation,
)


class _FakeConnection:
    def __init__(self):
        self.initialized = False


@pytest.mark.asyncio
async def test_connection_acquisition_happy_and_error_paths():
    connection_manager = _FakeConnection()
    helper = ConnectionAcquisitionHelper(helper_logger, connection_manager)
    redis_client = object()
    state = {"redis": redis_client, "ensure_calls": 0, "ping_result": (True, False)}

    def getter():
        return state.get("redis")

    async def ensure():
        state["ensure_calls"] += 1
        return state.get("ensure_ok", True)

    async def ping(client):
        return state["ping_result"]

    # Happy path with reconnect after missing redis
    state["redis"] = None
    state["ensure_ok"] = True
    state["redis_after"] = redis_client

    def getter_with_update():
        return state["redis"] or state.get("redis_after")

    client = await helper.get_redis(getter_with_update, ensure, ping)
    assert client is redis_client

    # Establishment failure
    state["redis"] = None
    state["redis_after"] = None
    state["ensure_ok"] = False
    with pytest.raises(TradeStoreError):
        await helper.get_redis(getter_with_update, ensure, ping)

    # Ping fatal error
    state["redis"] = redis_client
    state["redis_after"] = redis_client
    state["ensure_ok"] = True
    state["ping_result"] = (False, True)
    with pytest.raises(TradeStoreError):
        await helper.get_redis(getter_with_update, ensure, ping)


@pytest.mark.asyncio
async def test_create_connection_operation(monkeypatch):
    redis_client = object()
    connection_manager = _FakeConnection()
    calls = {"closed": 0, "reset": 0}

    async def pool_acquirer(allow_reuse):
        return redis_client

    async def verify_func(client):
        return (verify_func.ok, verify_func.fatal)

    verify_func.ok = True
    verify_func.fatal = False

    async def close_func(client, setter):
        calls["closed"] += 1

    def reset_func():
        calls["reset"] += 1

    op = create_connection_operation(
        ConnectionOperationConfig(
            connection_manager=connection_manager,
            pool_acquirer=pool_acquirer,
            verify_func=verify_func,
            close_func=close_func,
            reset_func=reset_func,
            redis_setter=None,
            context="ctx",
            attempts=2,
            allow_reuse=True,
            logger=helper_logger,
        )
    )

    helper_logger.debug("starting verify ok path")
    client = await op(1)
    assert client is redis_client
    assert connection_manager.initialized is True

    verify_func.ok = False
    verify_func.fatal = False
    with pytest.raises(TradeStoreError):
        await op(2)
    assert calls["closed"] == 1
    assert calls["reset"] == 1

    verify_func.fatal = True
    with pytest.raises(RedisFatalError):
        await op(3)


class _HelperLogger:
    def __init__(self):
        self.messages = []

    def debug(self, msg, *args, **kwargs):
        self.messages.append(msg)

    def __getattr__(self, name):
        # allow info/warning without extra logic
        return self.debug


helper_logger = _HelperLogger()
