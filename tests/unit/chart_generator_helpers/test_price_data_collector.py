"""Tests for price_data_collector module."""

import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_generator.exceptions import InsufficientDataError

# Test constants for price data
TEST_PRICE_BTC_INITIAL = 50000.0
TEST_PRICE_BTC_CURRENT = 51000.0
TEST_TIMESTAMP_OFFSET_SECONDS = 3600
TEST_HOURS_24_SECONDS = 86400


def _create_mock_tracker(price_data: list) -> MagicMock:
    """Create a mock PriceHistoryTracker with the given data."""
    mock_tracker = MagicMock()
    mock_tracker.initialize = AsyncMock()
    mock_tracker.cleanup = AsyncMock()
    mock_tracker.get_price_history = AsyncMock(return_value=price_data)
    return mock_tracker


class TestPriceDataCollectorViaSysModules:
    """Tests for PriceDataCollector using sys.modules injection."""

    @pytest.mark.asyncio
    async def test_collect_price_history_success(self) -> None:
        """Test successful price history collection via sys.modules."""
        now = int(datetime.now(timezone.utc).timestamp())
        mock_tracker = _create_mock_tracker(
            [
                (now - TEST_TIMESTAMP_OFFSET_SECONDS, TEST_PRICE_BTC_INITIAL),
                (now, TEST_PRICE_BTC_CURRENT),
            ]
        )
        mock_tracker_cls = MagicMock(return_value=mock_tracker)

        # Create a mock chart_generator module with PriceHistoryTracker
        mock_cg_module = MagicMock()
        mock_cg_module.PriceHistoryTracker = mock_tracker_cls

        # Import fresh
        if "common.chart_generator_helpers.price_data_collector" in sys.modules:
            del sys.modules["common.chart_generator_helpers.price_data_collector"]

        from common.chart_generator_helpers.price_data_collector import PriceDataCollector

        collector = PriceDataCollector()

        # Inject mock module into sys.modules for the tracker lookup
        with patch.dict(sys.modules, {"src.monitor.chart_generator": mock_cg_module}):
            timestamps, prices = await collector.collect_price_history("BTC")

        assert len(timestamps) >= 2
        assert len(prices) >= 2
        mock_tracker_cls.assert_called_once()
        mock_tracker.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_price_history_no_data(self) -> None:
        """Test raises error when no data available."""
        mock_tracker = _create_mock_tracker([])
        mock_tracker_cls = MagicMock(return_value=mock_tracker)

        mock_cg_module = MagicMock()
        mock_cg_module.PriceHistoryTracker = mock_tracker_cls

        if "common.chart_generator_helpers.price_data_collector" in sys.modules:
            del sys.modules["common.chart_generator_helpers.price_data_collector"]

        from common.chart_generator_helpers.price_data_collector import PriceDataCollector

        collector = PriceDataCollector()

        with patch.dict(sys.modules, {"src.monitor.chart_generator": mock_cg_module}):
            with pytest.raises(InsufficientDataError, match="No price data"):
                await collector.collect_price_history("BTC")

        mock_tracker.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_price_history_insufficient_data(self) -> None:
        """Test raises error when insufficient data points."""
        now = int(datetime.now(timezone.utc).timestamp())
        mock_tracker = _create_mock_tracker([(now, TEST_PRICE_BTC_INITIAL)])
        mock_tracker_cls = MagicMock(return_value=mock_tracker)

        mock_cg_module = MagicMock()
        mock_cg_module.PriceHistoryTracker = mock_tracker_cls

        if "common.chart_generator_helpers.price_data_collector" in sys.modules:
            del sys.modules["common.chart_generator_helpers.price_data_collector"]

        from common.chart_generator_helpers.price_data_collector import PriceDataCollector

        collector = PriceDataCollector()

        with patch.dict(sys.modules, {"src.monitor.chart_generator": mock_cg_module}):
            with pytest.raises(InsufficientDataError, match="Insufficient price data"):
                await collector.collect_price_history("ETH")

        mock_tracker.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_price_history_skips_invalid_data(self) -> None:
        """Test skips invalid data points."""
        now = int(datetime.now(timezone.utc).timestamp())
        mock_tracker = _create_mock_tracker(
            [
                (now - TEST_TIMESTAMP_OFFSET_SECONDS, TEST_PRICE_BTC_INITIAL),
                ("invalid", "invalid"),
                (now, TEST_PRICE_BTC_CURRENT),
            ]
        )
        mock_tracker_cls = MagicMock(return_value=mock_tracker)

        mock_cg_module = MagicMock()
        mock_cg_module.PriceHistoryTracker = mock_tracker_cls

        if "common.chart_generator_helpers.price_data_collector" in sys.modules:
            del sys.modules["common.chart_generator_helpers.price_data_collector"]

        from common.chart_generator_helpers.price_data_collector import PriceDataCollector

        collector = PriceDataCollector()

        with patch.dict(sys.modules, {"src.monitor.chart_generator": mock_cg_module}):
            timestamps, prices = await collector.collect_price_history("BTC")

        assert len(timestamps) >= 2
        mock_tracker.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_price_history_all_invalid_data(self) -> None:
        """Test raises error when all data points are invalid."""
        mock_tracker = _create_mock_tracker(
            [
                ("invalid", "invalid"),
                (None, None),
            ]
        )
        mock_tracker_cls = MagicMock(return_value=mock_tracker)

        mock_cg_module = MagicMock()
        mock_cg_module.PriceHistoryTracker = mock_tracker_cls

        if "common.chart_generator_helpers.price_data_collector" in sys.modules:
            del sys.modules["common.chart_generator_helpers.price_data_collector"]

        from common.chart_generator_helpers.price_data_collector import PriceDataCollector

        collector = PriceDataCollector()

        with patch.dict(sys.modules, {"src.monitor.chart_generator": mock_cg_module}):
            with pytest.raises(InsufficientDataError, match="No valid price data"):
                await collector.collect_price_history("BTC")

    @pytest.mark.asyncio
    async def test_collect_price_history_adds_synthetic_point_for_short_history(self) -> None:
        """Test adds synthetic data point when history is less than 24 hours."""
        now = int(datetime.now(timezone.utc).timestamp())
        # Only 1 hour of history
        mock_tracker = _create_mock_tracker(
            [
                (now - TEST_TIMESTAMP_OFFSET_SECONDS, TEST_PRICE_BTC_INITIAL),
                (now, TEST_PRICE_BTC_CURRENT),
            ]
        )
        mock_tracker_cls = MagicMock(return_value=mock_tracker)

        mock_cg_module = MagicMock()
        mock_cg_module.PriceHistoryTracker = mock_tracker_cls

        if "common.chart_generator_helpers.price_data_collector" in sys.modules:
            del sys.modules["common.chart_generator_helpers.price_data_collector"]

        from common.chart_generator_helpers.price_data_collector import PriceDataCollector

        collector = PriceDataCollector()

        with patch.dict(sys.modules, {"src.monitor.chart_generator": mock_cg_module}):
            timestamps, prices = await collector.collect_price_history("BTC")

        # Should have 3 points: synthetic + 2 real
        assert len(timestamps) == 3
        assert len(prices) == 3
        # First price should match the first real price (synthetic uses same value)
        assert prices[0] == prices[1]

    @pytest.mark.asyncio
    async def test_collect_price_history_no_synthetic_for_long_history(self) -> None:
        """Test no synthetic data point when history spans 24+ hours."""
        now = int(datetime.now(timezone.utc).timestamp())
        # 25 hours of history
        mock_tracker = _create_mock_tracker(
            [
                (now - TEST_HOURS_24_SECONDS - TEST_TIMESTAMP_OFFSET_SECONDS, TEST_PRICE_BTC_INITIAL),
                (now, TEST_PRICE_BTC_CURRENT),
            ]
        )
        mock_tracker_cls = MagicMock(return_value=mock_tracker)

        mock_cg_module = MagicMock()
        mock_cg_module.PriceHistoryTracker = mock_tracker_cls

        if "common.chart_generator_helpers.price_data_collector" in sys.modules:
            del sys.modules["common.chart_generator_helpers.price_data_collector"]

        from common.chart_generator_helpers.price_data_collector import PriceDataCollector

        collector = PriceDataCollector()

        with patch.dict(sys.modules, {"src.monitor.chart_generator": mock_cg_module}):
            timestamps, prices = await collector.collect_price_history("BTC")

        # Should have exactly 2 points (no synthetic)
        assert len(timestamps) == 2
        assert len(prices) == 2
