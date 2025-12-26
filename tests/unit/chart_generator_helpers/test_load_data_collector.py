"""Tests for chart_generator_helpers.load_data_collector module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.chart_generator.exceptions import InsufficientDataError
from common.chart_generator_helpers.load_data_collector import LoadDataCollector


class TestLoadDataCollectorCollectServiceLoadData:
    """Tests for collect_service_load_data method."""

    @pytest.mark.asyncio
    async def test_collects_messages_per_minute(self) -> None:
        """Test collects messages_per_minute data."""
        now = datetime.now(tz=timezone.utc)
        history_data = [
            {"timestamp": now, "messages_per_minute": 100.0},
            {"timestamp": now, "messages_per_minute": 150.0},
        ]

        with patch("common.chart_generator_helpers.load_data_collector.MetadataStore") as mock_store_class:
            mock_store = MagicMock()
            mock_store.initialize = AsyncMock()
            mock_store.get_service_history = AsyncMock(return_value=history_data)
            mock_store.cleanup = AsyncMock()
            mock_store_class.return_value = mock_store

            collector = LoadDataCollector()
            timestamps, values = await collector.collect_service_load_data("deribit", 24)

            assert len(timestamps) == 2
            assert values == [100.0, 150.0]
            mock_store.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_collects_messages_per_second(self) -> None:
        """Test collects messages_per_second data."""
        now = datetime.now(tz=timezone.utc)
        history_data = [
            {"timestamp": now, "messages_per_second": 10.0},
            {"timestamp": now, "messages_per_second": 15.0},
        ]

        with patch("common.chart_generator_helpers.load_data_collector.MetadataStore") as mock_store_class:
            mock_store = MagicMock()
            mock_store.initialize = AsyncMock()
            mock_store.get_service_history = AsyncMock(return_value=history_data)
            mock_store.cleanup = AsyncMock()
            mock_store_class.return_value = mock_store

            collector = LoadDataCollector()
            timestamps, values = await collector.collect_service_load_data("kalshi", 24)

            assert len(timestamps) == 2
            assert values == [10.0, 15.0]

    @pytest.mark.asyncio
    async def test_raises_on_empty_history(self) -> None:
        """Test raises InsufficientDataError on empty history."""
        with patch("common.chart_generator_helpers.load_data_collector.MetadataStore") as mock_store_class:
            mock_store = MagicMock()
            mock_store.initialize = AsyncMock()
            mock_store.get_service_history = AsyncMock(return_value=[])
            mock_store.cleanup = AsyncMock()
            mock_store_class.return_value = mock_store

            collector = LoadDataCollector()

            with pytest.raises(InsufficientDataError) as exc_info:
                await collector.collect_service_load_data("deribit", 24)

            assert "deribit" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_on_insufficient_data_points(self) -> None:
        """Test raises InsufficientDataError on insufficient data points."""
        now = datetime.now(tz=timezone.utc)
        history_data = [{"timestamp": now, "messages_per_minute": 100.0}]  # Only 1 point

        with patch("common.chart_generator_helpers.load_data_collector.MetadataStore") as mock_store_class:
            mock_store = MagicMock()
            mock_store.initialize = AsyncMock()
            mock_store.get_service_history = AsyncMock(return_value=history_data)
            mock_store.cleanup = AsyncMock()
            mock_store_class.return_value = mock_store

            collector = LoadDataCollector()

            with pytest.raises(InsufficientDataError) as exc_info:
                await collector.collect_service_load_data("deribit", 24)

            assert "Insufficient data points" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_skips_entries_without_message_data(self) -> None:
        """Test skips entries without message count data."""
        now = datetime.now(tz=timezone.utc)
        history_data = [
            {"timestamp": now, "other_field": 100.0},
            {"timestamp": now, "messages_per_minute": 150.0},
            {"timestamp": now, "messages_per_minute": 200.0},
        ]

        with patch("common.chart_generator_helpers.load_data_collector.MetadataStore") as mock_store_class:
            mock_store = MagicMock()
            mock_store.initialize = AsyncMock()
            mock_store.get_service_history = AsyncMock(return_value=history_data)
            mock_store.cleanup = AsyncMock()
            mock_store_class.return_value = mock_store

            collector = LoadDataCollector()
            timestamps, values = await collector.collect_service_load_data("deribit", 24)

            assert len(timestamps) == 2
            assert values == [150.0, 200.0]

    @pytest.mark.asyncio
    async def test_skips_invalid_numeric_values(self) -> None:
        """Test skips entries with invalid numeric values."""
        now = datetime.now(tz=timezone.utc)
        history_data = [
            {"timestamp": now, "messages_per_minute": "invalid"},
            {"timestamp": now, "messages_per_minute": 150.0},
            {"timestamp": now, "messages_per_minute": 200.0},
        ]

        with patch("common.chart_generator_helpers.load_data_collector.MetadataStore") as mock_store_class:
            mock_store = MagicMock()
            mock_store.initialize = AsyncMock()
            mock_store.get_service_history = AsyncMock(return_value=history_data)
            mock_store.cleanup = AsyncMock()
            mock_store_class.return_value = mock_store

            collector = LoadDataCollector()
            timestamps, values = await collector.collect_service_load_data("deribit", 24)

            assert len(timestamps) == 2
            assert values == [150.0, 200.0]

    @pytest.mark.asyncio
    async def test_skips_zero_values(self) -> None:
        """Test skips entries with zero values."""
        now = datetime.now(tz=timezone.utc)
        history_data = [
            {"timestamp": now, "messages_per_minute": 0.0},
            {"timestamp": now, "messages_per_minute": 150.0},
            {"timestamp": now, "messages_per_minute": 200.0},
        ]

        with patch("common.chart_generator_helpers.load_data_collector.MetadataStore") as mock_store_class:
            mock_store = MagicMock()
            mock_store.initialize = AsyncMock()
            mock_store.get_service_history = AsyncMock(return_value=history_data)
            mock_store.cleanup = AsyncMock()
            mock_store_class.return_value = mock_store

            collector = LoadDataCollector()
            timestamps, values = await collector.collect_service_load_data("deribit", 24)

            assert len(timestamps) == 2
            assert values == [150.0, 200.0]

    @pytest.mark.asyncio
    async def test_cleanup_called_on_exception(self) -> None:
        """Test cleanup is called even on exception."""
        with patch("common.chart_generator_helpers.load_data_collector.MetadataStore") as mock_store_class:
            mock_store = MagicMock()
            mock_store.initialize = AsyncMock()
            mock_store.get_service_history = AsyncMock(return_value=[])
            mock_store.cleanup = AsyncMock()
            mock_store_class.return_value = mock_store

            collector = LoadDataCollector()

            with pytest.raises(InsufficientDataError):
                await collector.collect_service_load_data("deribit", 24)

            mock_store.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_prefers_messages_per_minute(self) -> None:
        """Test prefers messages_per_minute over messages_per_second."""
        now = datetime.now(tz=timezone.utc)
        history_data = [
            {"timestamp": now, "messages_per_minute": 100.0, "messages_per_second": 1.0},
            {"timestamp": now, "messages_per_minute": 150.0, "messages_per_second": 2.0},
        ]

        with patch("common.chart_generator_helpers.load_data_collector.MetadataStore") as mock_store_class:
            mock_store = MagicMock()
            mock_store.initialize = AsyncMock()
            mock_store.get_service_history = AsyncMock(return_value=history_data)
            mock_store.cleanup = AsyncMock()
            mock_store_class.return_value = mock_store

            collector = LoadDataCollector()
            timestamps, values = await collector.collect_service_load_data("deribit", 24)

            assert values == [100.0, 150.0]  # Uses messages_per_minute
