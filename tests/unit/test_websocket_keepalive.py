"""Tests for thread-based websocket keepalive."""

import asyncio

import pytest

from common.websocket_keepalive import KeepaliveError, run_threaded_keepalive


class TestRunThreadedKeepalive:
    """Tests for run_threaded_keepalive."""

    @pytest.mark.asyncio
    async def test_exits_cleanly_on_shutdown(self) -> None:
        """Returns normally when is_shutdown becomes True."""

        async def ping_fn() -> None:
            pass

        await run_threaded_keepalive(
            ping_fn=ping_fn,
            interval=0,
            ping_timeout=1,
            is_shutdown=lambda: True,
            thread_name="test",
        )

    @pytest.mark.asyncio
    async def test_raises_on_connection_error(self) -> None:
        """Raises KeepaliveError when ping raises ConnectionError."""

        async def ping_fn() -> None:
            raise ConnectionError("ws is None")

        with pytest.raises(KeepaliveError):
            await run_threaded_keepalive(
                ping_fn=ping_fn,
                interval=0,
                ping_timeout=1,
                is_shutdown=lambda: False,
                thread_name="test",
            )

    @pytest.mark.asyncio
    async def test_raises_after_max_missed_pongs(self) -> None:
        """Raises KeepaliveError after max missed pongs from timeouts."""

        async def ping_fn() -> None:
            await asyncio.sleep(10)

        with pytest.raises(KeepaliveError):
            await run_threaded_keepalive(
                ping_fn=ping_fn,
                interval=0,
                ping_timeout=0,
                max_missed=1,
                is_shutdown=lambda: False,
                thread_name="test",
            )

    @pytest.mark.asyncio
    async def test_successful_ping_resets_missed_count(self) -> None:
        """Successful pings reset the missed counter; loop exits on shutdown."""
        call_count = {"n": 0}

        async def ping_fn() -> None:
            call_count["n"] += 1

        def is_shutdown() -> bool:
            return call_count["n"] >= 3

        await run_threaded_keepalive(
            ping_fn=ping_fn,
            interval=0,
            ping_timeout=1,
            is_shutdown=is_shutdown,
            thread_name="test",
        )

        assert call_count["n"] >= 3
