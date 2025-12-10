"""Unit tests for message_metrics_collector."""

import asyncio
from typing import NamedTuple
from unittest.mock import AsyncMock, Mock, patch

import pytest
from redis.exceptions import RedisError

from common.exceptions import DataError
from common.optimized_status_reporter_helpers.message_metrics_collector import (
    STATUS_REPORT_ERRORS,
    MessageMetricsCollector,
)
from common.redis_utils import RedisOperationError


class MockMetadata(NamedTuple):
    messages_last_minute: int = 0
    messages_last_65_minutes: int = 0


class TestMessageMetricsCollector:
    """Tests for MessageMetricsCollector."""

    @pytest.fixture
    def mock_realtime_collector(self):
        """Mock RealtimeMetricsCollector."""
        collector = Mock()
        collector.get_deribit_sum_last_60_seconds = AsyncMock(return_value=100)
        collector.get_kalshi_sum_last_60_seconds = AsyncMock(return_value=50)
        return collector

    @pytest.fixture
    def mock_metadata_store(self):
        """Mock metadata store."""
        store = Mock()
        store.get_service_metadata = AsyncMock(
            side_effect=[
                MockMetadata(messages_last_minute=10),  # cfb
                MockMetadata(messages_last_65_minutes=20),  # asos
                MockMetadata(messages_last_65_minutes=30),  # metar
            ]
        )
        return store

    @pytest.fixture
    def collector(self, mock_realtime_collector, mock_metadata_store):
        """MessageMetricsCollector instance with mocked dependencies."""
        return MessageMetricsCollector(mock_realtime_collector, mock_metadata_store)

    @pytest.mark.asyncio
    async def test_collect_message_metrics_success(
        self, collector, mock_realtime_collector, mock_metadata_store
    ):
        """Test successful collection of all message metrics."""
        result = await collector.collect_message_metrics()

        mock_realtime_collector.get_deribit_sum_last_60_seconds.assert_awaited_once()
        mock_realtime_collector.get_kalshi_sum_last_60_seconds.assert_awaited_once()
        mock_metadata_store.get_service_metadata.assert_any_call("cfb")
        mock_metadata_store.get_service_metadata.assert_any_call("asos")
        mock_metadata_store.get_service_metadata.assert_any_call("metar")

        assert result == {
            "deribit_messages_60s": 100,
            "kalshi_messages_60s": 50,
            "cfb_messages_60s": 10,
            "asos_messages_65m": 20,
            "metar_messages_65m": 30,
        }

    @pytest.mark.parametrize("exception_class", STATUS_REPORT_ERRORS)
    @pytest.mark.asyncio
    async def test_collect_message_metrics_realtime_failure(
        self, collector, mock_realtime_collector, exception_class
    ):
        """Test realtime metrics collection failure raises RuntimeError."""
        mock_realtime_collector.get_deribit_sum_last_60_seconds.side_effect = exception_class(
            "Test error"
        )

        with pytest.raises(RuntimeError, match="Failed to collect realtime message metrics"):
            await collector.collect_message_metrics()

    @pytest.mark.parametrize("exception_class", STATUS_REPORT_ERRORS)
    @pytest.mark.asyncio
    async def test_collect_message_metrics_metadata_failure(
        self, collector, mock_metadata_store, exception_class
    ):
        """Test metadata metrics collection failure raises DataError."""
        mock_metadata_store.get_service_metadata.side_effect = exception_class("Test error")

        with pytest.raises(DataError, match="Failed to collect metadata message metrics"):
            await collector.collect_message_metrics()

    def test_require_metadata_value_result_none(self, collector):
        """Test _require_metadata_value raises DataError if result is None."""
        with pytest.raises(DataError, match="Metadata for cfb service is unavailable"):
            collector._require_metadata_value("cfb", None, "messages_last_minute")

    def test_require_metadata_value_attribute_error(self, collector):
        """Test _require_metadata_value raises DataError if attribute missing."""
        with pytest.raises(DataError, match="missing required attribute"):
            collector._require_metadata_value("cfb", MockMetadata(), "non_existent_attribute")

    def test_require_metadata_value_value_none(self, collector):
        """Test _require_metadata_value raises DataError if attribute value is None."""
        # Create a MockMetadata that returns None for a specific attribute
        mock_obj = MockMetadata(messages_last_minute=None)
        with pytest.raises(DataError, match="has null value"):
            collector._require_metadata_value("cfb", mock_obj, "messages_last_minute")

    @pytest.mark.parametrize(
        "value, _exception_type",
        [
            ("non-numeric", ValueError),
            (Mock(), TypeError),
        ],
    )
    def test_require_metadata_value_non_numeric(self, collector, value, _exception_type):
        """Test _require_metadata_value raises DataError for non-numeric value."""
        # Create a mock object whose attribute returns a non-numeric value
        mock_obj = MockMetadata(messages_last_minute=value)
        with pytest.raises(DataError, match="contains non-numeric value"):
            collector._require_metadata_value("cfb", mock_obj, "messages_last_minute")
