"""Tests for orderbook operations module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.kalshi_store.reader_helpers.orderbook_operations import (
    get_orderbook_side_with_connection_check,
    get_orderbook_with_connection_check,
)


class TestGetOrderbookWithConnectionCheck:
    """Tests for get_orderbook_with_connection_check function."""

    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_connection_fails(self) -> None:
        """Returns empty dict when connection check fails."""
        mock_conn = AsyncMock()
        mock_conn.ensure_connection.return_value = False

        mock_reader = AsyncMock()
        mock_key_fn = MagicMock(return_value="markets:kalshi:temp:KXTEMP-TEST")

        result = await get_orderbook_with_connection_check(mock_conn, mock_reader, "KXTEMP-TEST", mock_key_fn)

        assert result == {}
        mock_reader.get_orderbook.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_orderbook_when_connected(self) -> None:
        """Returns orderbook data when connection succeeds."""
        mock_conn = AsyncMock()
        mock_conn.ensure_connection.return_value = True
        mock_redis = AsyncMock()
        mock_conn.get_redis.return_value = mock_redis

        mock_reader = AsyncMock()
        expected_orderbook = {"bids": [], "asks": []}
        mock_reader.get_orderbook.return_value = expected_orderbook
        mock_key_fn = MagicMock(return_value="markets:kalshi:temp:KXTEMP-TEST")

        result = await get_orderbook_with_connection_check(mock_conn, mock_reader, "KXTEMP-TEST", mock_key_fn)

        assert result == expected_orderbook
        mock_reader.get_orderbook.assert_called_once()


class TestGetOrderbookSideWithConnectionCheck:
    """Tests for get_orderbook_side_with_connection_check function."""

    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_connection_fails(self) -> None:
        """Returns empty dict when connection check fails."""
        mock_conn = AsyncMock()
        mock_conn.ensure_connection.return_value = False

        mock_reader = AsyncMock()
        mock_key_fn = MagicMock(return_value="markets:kalshi:temp:KXTEMP-TEST")

        result = await get_orderbook_side_with_connection_check(mock_conn, mock_reader, "KXTEMP-TEST", "bids", mock_key_fn)

        assert result == {}
        mock_reader.get_orderbook_side.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_orderbook_side_when_connected(self) -> None:
        """Returns orderbook side data when connection succeeds."""
        mock_conn = AsyncMock()
        mock_conn.ensure_connection.return_value = True
        mock_redis = AsyncMock()
        mock_conn.get_redis.return_value = mock_redis

        mock_reader = AsyncMock()
        expected_side = {"levels": []}
        mock_reader.get_orderbook_side.return_value = expected_side
        mock_key_fn = MagicMock(return_value="markets:kalshi:temp:KXTEMP-TEST")

        result = await get_orderbook_side_with_connection_check(mock_conn, mock_reader, "KXTEMP-TEST", "bids", mock_key_fn)

        assert result == expected_side
        mock_reader.get_orderbook_side.assert_called_once()
