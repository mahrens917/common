import pytest

from common.utils.distributed_lock import (
    DistributedLock,
    LockUnavailableError,
    create_liquidation_lock,
    create_trade_lock,
)

_CONST_15 = 15
_CONST_60 = 60


class StubRedisClient:
    def __init__(
        self,
        *,
        set_result: bool | None = True,
        set_exception: Exception | None = None,
        delete_exception: Exception | None = None,
        get_override: dict[str, str] | None = None,
    ) -> None:
        self.set_result = set_result
        self.set_exception = set_exception
        self.delete_exception = delete_exception
        self.set_calls: list[tuple[str, str, int, bool]] = []
        self.delete_calls: list[str] = []
        self._store: dict[str, str] = get_override or {}

    async def set(self, key: str, value: str, *, ex: int, nx: bool) -> bool | None:
        self.set_calls.append((key, value, ex, nx))
        if self.set_exception is not None:
            raise self.set_exception
        if self.set_result:
            self._store[key] = value
        return self.set_result

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def delete(self, key: str) -> None:
        self.delete_calls.append(key)
        if self.delete_exception is not None:
            raise self.delete_exception
        self._store.pop(key, None)


@pytest.mark.asyncio
async def test_acquire_success_records_lock_and_returns_true() -> None:
    stub = StubRedisClient()
    lock = DistributedLock(stub, "lock:key", timeout_seconds=42)

    acquired = await lock.acquire()

    assert acquired is True
    assert stub.set_calls == [("lock:key", lock.lock_value, 42, True)]
    assert await stub.get("lock:key") == lock.lock_value


@pytest.mark.asyncio
async def test_acquire_raises_when_redis_rejects() -> None:
    stub = StubRedisClient(set_result=False)
    lock = DistributedLock(stub, "shared:key")

    with pytest.raises(LockUnavailableError):
        await lock.acquire()
    assert stub.delete_calls == []


@pytest.mark.asyncio
async def test_acquire_raises_on_error() -> None:
    stub = StubRedisClient(set_exception=RuntimeError("boom"))
    lock = DistributedLock(stub, "error:key")

    with pytest.raises(LockUnavailableError):
        await lock.acquire()


@pytest.mark.asyncio
async def test_acquire_raises_when_redis_missing() -> None:
    lock = DistributedLock(None, "no-redis")

    with pytest.raises(LockUnavailableError):
        await lock.acquire()


@pytest.mark.asyncio
async def test_release_deletes_key_when_acquired() -> None:
    stub = StubRedisClient()
    lock = DistributedLock(stub, "release:key")

    assert await lock.acquire() is True
    await lock.release()

    assert stub.delete_calls == ["release:key"]
    assert await stub.get("release:key") is None


@pytest.mark.asyncio
async def test_release_handles_delete_error() -> None:
    stub = StubRedisClient(delete_exception=RuntimeError("cannot delete"))
    lock = DistributedLock(stub, "delete:error")

    assert await lock.acquire() is True
    with pytest.raises(LockUnavailableError):
        await lock.release()


@pytest.mark.asyncio
async def test_acquire_context_releases_lock_on_exit() -> None:
    stub = StubRedisClient()
    lock = DistributedLock(stub, "ctx:key")

    async with lock.acquire_context():
        assert lock._acquired is True

    assert stub.delete_calls == ["ctx:key"]
    assert lock._acquired is False


@pytest.mark.asyncio
async def test_acquire_context_raises_when_unavailable() -> None:
    stub = StubRedisClient(set_result=False)
    lock = DistributedLock(stub, "ctx:fail")

    with pytest.raises(LockUnavailableError):
        async with lock.acquire_context():
            pass


@pytest.mark.asyncio
async def test_create_trade_lock_builds_expected_key() -> None:
    stub = StubRedisClient()
    lock = await create_trade_lock(stub, "TST", timeout_seconds=15)

    assert isinstance(lock, DistributedLock)
    assert lock.lock_key == "trade_lock:TST"
    assert lock.timeout_seconds == _CONST_15


@pytest.mark.asyncio
async def test_create_liquidation_lock_uses_default_timeout() -> None:
    stub = StubRedisClient()
    lock = await create_liquidation_lock(stub, "TST")

    assert isinstance(lock, DistributedLock)
    assert lock.lock_key == "liquidation_lock:TST"
    assert lock.timeout_seconds == _CONST_60
