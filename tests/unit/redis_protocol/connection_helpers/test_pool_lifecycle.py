"""Tests for pool lifecycle module."""

import asyncio
import weakref
from unittest.mock import MagicMock

import pytest

from common.redis_protocol.connection_helpers.pool_lifecycle import should_rebuild_pool


class TestShouldRebuildPool:
    """Tests for should_rebuild_pool function."""

    @pytest.mark.asyncio
    async def test_returns_false_when_pool_is_none(self) -> None:
        """Returns False when pool is None."""
        current_loop = asyncio.get_event_loop()

        result = await should_rebuild_pool(None, None, current_loop)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_pool_loop_is_none(self) -> None:
        """Returns False when pool_loop is None."""
        mock_pool = MagicMock()
        current_loop = asyncio.get_event_loop()

        result = await should_rebuild_pool(mock_pool, None, current_loop)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_cached_loop_is_none(self) -> None:
        """Returns True when cached loop reference returns None."""
        mock_pool = MagicMock()
        current_loop = asyncio.get_event_loop()
        dead_ref = weakref.ref(MagicMock())

        result = await should_rebuild_pool(mock_pool, dead_ref, current_loop)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_when_cached_loop_is_closed(self) -> None:
        """Returns True when cached loop is closed."""
        mock_pool = MagicMock()
        current_loop = asyncio.get_event_loop()
        mock_cached_loop = MagicMock()
        mock_cached_loop.is_closed.return_value = True
        pool_loop = MagicMock(return_value=mock_cached_loop)

        result = await should_rebuild_pool(mock_pool, pool_loop, current_loop)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_when_loop_mismatch(self) -> None:
        """Returns True when cached loop differs from current loop."""
        mock_pool = MagicMock()
        current_loop = asyncio.get_event_loop()
        different_loop = MagicMock()
        different_loop.is_closed.return_value = False
        pool_loop = MagicMock(return_value=different_loop)

        result = await should_rebuild_pool(mock_pool, pool_loop, current_loop)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_same_open_loop(self) -> None:
        """Returns False when cached loop matches current open loop."""
        mock_pool = MagicMock()
        current_loop = asyncio.get_event_loop()
        pool_loop = weakref.ref(current_loop)

        result = await should_rebuild_pool(mock_pool, pool_loop, current_loop)

        assert result is False
