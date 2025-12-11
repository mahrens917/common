"""Tests for snapshot operations module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.redis_protocol.kalshi_store.reader_helpers.snapshot_operations import (
    fetch_market_field,
    fetch_market_metadata,
    fetch_market_snapshot,
)


class TestFetchMarketSnapshot:
    """Tests for fetch_market_snapshot function."""

    @pytest.mark.asyncio
    async def test_delegates_to_snapshot_reader(self) -> None:
        """Delegates to snapshot_reader.get_market_snapshot."""
        mock_redis = AsyncMock()
        mock_reader = AsyncMock()
        expected_snapshot = {"ticker": "KXTEMP-TEST", "best_bid": 50}
        mock_reader.get_market_snapshot.return_value = expected_snapshot

        result = await fetch_market_snapshot(mock_redis, "markets:kalshi:temp:KXTEMP-TEST", "KXTEMP-TEST", mock_reader)

        assert result == expected_snapshot
        mock_reader.get_market_snapshot.assert_called_once_with(
            mock_redis,
            "markets:kalshi:temp:KXTEMP-TEST",
            "KXTEMP-TEST",
            include_orderbook=True,
        )

    @pytest.mark.asyncio
    async def test_passes_include_orderbook_flag(self) -> None:
        """Passes include_orderbook flag to snapshot reader."""
        mock_redis = AsyncMock()
        mock_reader = AsyncMock()
        mock_reader.get_market_snapshot.return_value = {}

        await fetch_market_snapshot(
            mock_redis,
            "markets:kalshi:temp:KXTEMP-TEST",
            "KXTEMP-TEST",
            mock_reader,
            include_orderbook=False,
        )

        mock_reader.get_market_snapshot.assert_called_once_with(
            mock_redis,
            "markets:kalshi:temp:KXTEMP-TEST",
            "KXTEMP-TEST",
            include_orderbook=False,
        )


class TestFetchMarketMetadata:
    """Tests for fetch_market_metadata function."""

    @pytest.mark.asyncio
    async def test_delegates_to_snapshot_reader(self) -> None:
        """Delegates to snapshot_reader.get_market_metadata."""
        mock_redis = AsyncMock()
        mock_reader = AsyncMock()
        expected_metadata = {"ticker": "KXTEMP-TEST", "status": "active"}
        mock_reader.get_market_metadata.return_value = expected_metadata

        result = await fetch_market_metadata(mock_redis, "markets:kalshi:temp:KXTEMP-TEST", "KXTEMP-TEST", mock_reader)

        assert result == expected_metadata
        mock_reader.get_market_metadata.assert_called_once_with(mock_redis, "markets:kalshi:temp:KXTEMP-TEST", "KXTEMP-TEST")


class TestFetchMarketField:
    """Tests for fetch_market_field function."""

    @pytest.mark.asyncio
    async def test_delegates_to_snapshot_reader(self) -> None:
        """Delegates to snapshot_reader.get_market_field."""
        mock_redis = AsyncMock()
        mock_reader = AsyncMock()
        mock_reader.get_market_field.return_value = "active"

        result = await fetch_market_field(mock_redis, "markets:kalshi:temp:KXTEMP-TEST", "KXTEMP-TEST", "status", mock_reader)

        assert result == "active"
        mock_reader.get_market_field.assert_called_once_with(mock_redis, "markets:kalshi:temp:KXTEMP-TEST", "KXTEMP-TEST", "status")
