"""Tests for price_data_collector module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_generator.exceptions import InsufficientDataError
from common.chart_generator_helpers.price_data_collector import PriceDataCollector


class TestPriceDataCollector:
    """Tests for PriceDataCollector class."""

    @pytest.mark.asyncio
    async def test_collect_price_history_success(self) -> None:
        """Test successful price history collection."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_tracker.cleanup = AsyncMock()
        now = int(datetime.now(timezone.utc).timestamp())
        mock_tracker.get_price_history = AsyncMock(
            return_value=[
                (now - 3600, 50000.0),
                (now, 51000.0),
            ]
        )

        collector = PriceDataCollector()

        with patch(
            "common.chart_generator_helpers.price_data_collector.PriceHistoryTracker",
            return_value=mock_tracker,
        ):
            timestamps, prices = await collector.collect_price_history("BTC")

        assert len(timestamps) >= 2
        assert len(prices) >= 2
        mock_tracker.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_price_history_no_data(self) -> None:
        """Test raises error when no data available."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_tracker.cleanup = AsyncMock()
        mock_tracker.get_price_history = AsyncMock(return_value=[])

        collector = PriceDataCollector()

        with patch(
            "common.chart_generator_helpers.price_data_collector.PriceHistoryTracker",
            return_value=mock_tracker,
        ):
            with pytest.raises(InsufficientDataError, match="No price data"):
                await collector.collect_price_history("BTC")

        mock_tracker.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_price_history_insufficient_data(self) -> None:
        """Test raises error when insufficient data points."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_tracker.cleanup = AsyncMock()
        now = int(datetime.now(timezone.utc).timestamp())
        mock_tracker.get_price_history = AsyncMock(return_value=[(now, 50000.0)])

        collector = PriceDataCollector()

        with patch(
            "common.chart_generator_helpers.price_data_collector.PriceHistoryTracker",
            return_value=mock_tracker,
        ):
            with pytest.raises(InsufficientDataError, match="Insufficient price data"):
                await collector.collect_price_history("ETH")

        mock_tracker.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_price_history_skips_invalid_data(self) -> None:
        """Test skips invalid data points."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_tracker.cleanup = AsyncMock()
        now = int(datetime.now(timezone.utc).timestamp())
        mock_tracker.get_price_history = AsyncMock(
            return_value=[
                (now - 3600, 50000.0),
                ("invalid", "invalid"),
                (now, 51000.0),
            ]
        )

        collector = PriceDataCollector()

        with patch(
            "common.chart_generator_helpers.price_data_collector.PriceHistoryTracker",
            return_value=mock_tracker,
        ):
            timestamps, prices = await collector.collect_price_history("BTC")

        assert len(timestamps) >= 2
        mock_tracker.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_price_history_all_invalid_data(self) -> None:
        """Test raises error when all data points are invalid."""
        mock_tracker = MagicMock()
        mock_tracker.initialize = AsyncMock()
        mock_tracker.cleanup = AsyncMock()
        mock_tracker.get_price_history = AsyncMock(
            return_value=[
                ("invalid", "invalid"),
                (None, None),
            ]
        )

        collector = PriceDataCollector()

        with patch(
            "common.chart_generator_helpers.price_data_collector.PriceHistoryTracker",
            return_value=mock_tracker,
        ):
            with pytest.raises(InsufficientDataError, match="No valid price data"):
                await collector.collect_price_history("BTC")
