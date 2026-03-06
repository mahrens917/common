"""Tests for CoalescingBatcher."""

import asyncio
import logging

import pytest
from redis.exceptions import RedisError

from common.redis_protocol.coalescing_batcher import CoalescingBatcher

FLUSH_WAIT_S = 0.25


class TestAdd:
    def test_add_stores_by_key(self) -> None:
        batcher: CoalescingBatcher[str, int] = CoalescingBatcher(lambda _: None, "test")  # type: ignore[arg-type]
        batcher.add("a", 1)
        assert batcher._pending == {"a": 1}

    def test_add_overwrites_same_key(self) -> None:
        batcher: CoalescingBatcher[str, int] = CoalescingBatcher(lambda _: None, "test")  # type: ignore[arg-type]
        batcher.add("a", 1)
        batcher.add("a", 2)
        assert batcher._pending == {"a": 2}

    def test_add_multiple_keys(self) -> None:
        batcher: CoalescingBatcher[str, int] = CoalescingBatcher(lambda _: None, "test")  # type: ignore[arg-type]
        batcher.add("a", 1)
        batcher.add("b", 2)
        assert batcher._pending == {"a": 1, "b": 2}


class TestFlush:
    @pytest.mark.asyncio
    async def test_flush_calls_process_batch(self) -> None:
        received: list[list[int]] = []

        async def process(batch: list[int]) -> None:
            received.append(batch)

        batcher: CoalescingBatcher[str, int] = CoalescingBatcher(process, "test")
        batcher.add("a", 1)
        batcher.add("b", 2)
        await batcher._flush()
        assert len(received) == 1
        assert sorted(received[0]) == [1, 2]

    @pytest.mark.asyncio
    async def test_flush_clears_pending(self) -> None:
        async def process(batch: list[int]) -> None:
            pass

        batcher: CoalescingBatcher[str, int] = CoalescingBatcher(process, "test")
        batcher.add("a", 1)
        await batcher._flush()
        assert batcher._pending == {}

    @pytest.mark.asyncio
    async def test_flush_noop_when_empty(self) -> None:
        call_count = 0

        async def process(batch: list[int]) -> None:
            nonlocal call_count
            call_count += 1

        batcher: CoalescingBatcher[str, int] = CoalescingBatcher(process, "test")
        await batcher._flush()
        assert call_count == 0

    @pytest.mark.asyncio
    async def test_flush_merges_back_on_redis_error(self) -> None:
        async def process(batch: list[int]) -> None:
            raise RedisError("connection lost")

        batcher: CoalescingBatcher[str, int] = CoalescingBatcher(process, "test")
        batcher.add("a", 1)
        with pytest.raises(RedisError):
            await batcher._flush()
        assert batcher._pending == {"a": 1}

    @pytest.mark.asyncio
    async def test_flush_merge_preserves_new_arrivals(self) -> None:
        """Items added during a failed flush are not lost."""
        batcher: CoalescingBatcher[str, int] = CoalescingBatcher[str, int].__new__(CoalescingBatcher)
        batcher._name = "test"
        batcher._pending = {"a": 1}

        async def process(batch: list[int]) -> None:
            batcher._pending["b"] = 2
            raise RedisError("fail")

        batcher._process_batch = process
        with pytest.raises(RedisError):
            await batcher._flush()
        assert batcher._pending == {"a": 1, "b": 2}


class TestAtomicSwap:
    @pytest.mark.asyncio
    async def test_updates_during_flush_preserved(self) -> None:
        """Updates added while process_batch awaits must survive."""

        async def slow_process(batch: list[int]) -> None:
            await asyncio.sleep(0.01)

        batcher: CoalescingBatcher[str, int] = CoalescingBatcher(slow_process, "test")
        batcher.add("a", 1)

        async def add_during_flush() -> None:
            await asyncio.sleep(0.005)
            batcher.add("b", 2)

        await asyncio.gather(batcher._flush(), add_during_flush())
        assert "b" in batcher._pending


class TestStop:
    @pytest.mark.asyncio
    async def test_stop_flushes_remaining(self) -> None:
        received: list[list[int]] = []

        async def process(batch: list[int]) -> None:
            received.append(batch)

        batcher: CoalescingBatcher[str, int] = CoalescingBatcher(process, "test")
        await batcher.start()
        batcher.add("a", 1)
        await batcher.stop()
        assert len(received) >= 1
        assert 1 in received[-1]

    @pytest.mark.asyncio
    async def test_stop_warns_on_unflushed(self, caplog: pytest.LogCaptureFixture) -> None:
        async def process(batch: list[int]) -> None:
            raise RedisError("fail")

        batcher: CoalescingBatcher[str, int] = CoalescingBatcher(process, "test")
        batcher.add("a", 1)
        with caplog.at_level(logging.WARNING):
            await batcher.stop()
        assert "unflushed" in caplog.text


class TestTimer:
    @pytest.mark.asyncio
    async def test_flush_loop_fires(self) -> None:
        call_count = 0

        async def process(batch: list[str]) -> None:
            nonlocal call_count
            call_count += 1

        batcher: CoalescingBatcher[str, str] = CoalescingBatcher(process, "test")
        await batcher.start()
        batcher.add("a", "v1")
        await asyncio.sleep(FLUSH_WAIT_S)
        await batcher.stop()
        assert call_count >= 1
