"""Unit tests for status_data_aggregator."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.common.optimized_status_reporter_helpers.status_data_aggregator import (
    StatusDataAggregator,
    StatusDataCollectors,
)


class TestStatusDataAggregator:
    """Tests for StatusDataAggregator."""

    @pytest.fixture
    def mock_collectors(self):
        """Mock all individual collectors."""
        return StatusDataCollectors(
            service_collector=Mock(
                collect_running_services=AsyncMock(return_value={"service_A": {"pid": 123}})
            ),
            health_collector=Mock(
                collect_health_snapshot=AsyncMock(return_value={"redis_connection_healthy": True})
            ),
            key_counter=Mock(collect_key_counts=AsyncMock(return_value={"key_count_A": 10})),
            message_collector=Mock(
                collect_message_metrics=AsyncMock(return_value={"msg_metric_A": 1})
            ),
            price_collector=Mock(collect_price_data=AsyncMock(return_value={"price_data_A": 100})),
            weather_collector=Mock(
                collect_weather_temperatures=AsyncMock(return_value={"weather_temp_A": "70F"})
            ),
            log_collector=Mock(
                collect_log_activity_map=AsyncMock(
                    return_value=({"log_A": "activity"}, {"stale_A": True})
                )
            ),
            tracker_collector=Mock(
                collect_tracker_status=AsyncMock(return_value={"tracker_A": "running"}),
                merge_tracker_service_state=Mock(
                    return_value={
                        "service_A": {"pid": 123},
                        "tracker_service": {"status": "running"},
                    }
                ),
            ),
            kalshi_collector=Mock(
                get_kalshi_market_status=AsyncMock(return_value={"kalshi_status_A": "active"})
            ),
        )

    @pytest.fixture
    def aggregator(self, mock_collectors):
        """Return a StatusDataAggregator instance with mocked collectors."""
        return StatusDataAggregator(mock_collectors)

    @pytest.mark.asyncio
    async def test_gather_status_data(self, aggregator, mock_collectors):
        """Test gather_status_data collects data from all sources and aggregates correctly."""
        mock_redis_client = Mock()
        mock_process_monitor = Mock()
        mock_kalshi_client = Mock()

        # Mock resolve_redis_pid to return a PID
        aggregator._resolve_redis_pid = AsyncMock(return_value=456)

        # Call the method under test
        result = await aggregator.gather_status_data(
            mock_redis_client, mock_process_monitor, mock_kalshi_client
        )

        # Assert internal collectors are called
        mock_collectors.service_collector.collect_running_services.assert_awaited_once()
        mock_collectors.health_collector.collect_health_snapshot.assert_awaited_once()
        mock_collectors.key_counter.collect_key_counts.assert_awaited_once()
        mock_collectors.message_collector.collect_message_metrics.assert_awaited_once()
        mock_collectors.price_collector.collect_price_data.assert_awaited_once()
        mock_collectors.weather_collector.collect_weather_temperatures.assert_awaited_once()
        mock_collectors.log_collector.collect_log_activity_map.assert_awaited_once()
        mock_collectors.tracker_collector.collect_tracker_status.assert_awaited_once()
        mock_collectors.kalshi_collector.get_kalshi_market_status.assert_awaited_once()
        aggregator._resolve_redis_pid.assert_awaited_once_with(mock_process_monitor)

        # Assert redis_client is set on relevant collectors
        assert mock_collectors.key_counter.redis_client == mock_redis_client
        assert mock_collectors.message_collector.redis_client == mock_redis_client
        assert (
            mock_collectors.message_collector.realtime_collector.redis_client == mock_redis_client
        )
        assert mock_collectors.price_collector.redis_client == mock_redis_client
        assert mock_collectors.weather_collector.redis_client == mock_redis_client
        assert mock_collectors.kalshi_collector.redis_client == mock_redis_client

        # Assert correct aggregation and structure of the result
        assert result == {
            "redis_process": {"pid": 456},
            "running_services": {
                "service_A": {"pid": 123},
                "tracker_service": {"status": "running"},
            },
            "redis_connection_healthy": True,
            "key_count_A": 10,
            "msg_metric_A": 1,
            "weather_temperatures": {"weather_temp_A": "70F"},
            "stale_logs": {"stale_A": True},
            "log_activity": {"log_A": "activity"},
            "price_data_A": 100,
            "kalshi_market_status": {"kalshi_status_A": "active"},
            "tracker_status": {"tracker_A": "running"},
        }

    @pytest.mark.asyncio
    async def test_resolve_redis_pid_with_processes(self, aggregator):
        """Test _resolve_redis_pid returns PID when processes are found."""
        mock_process_monitor = Mock()
        mock_process_monitor.get_redis_processes = AsyncMock(return_value=[Mock(pid=789)])

        pid = await aggregator._resolve_redis_pid(mock_process_monitor)

        assert pid == 789
        mock_process_monitor.get_redis_processes.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resolve_redis_pid_without_processes(self, aggregator):
        """Test _resolve_redis_pid returns None when no processes are found."""
        mock_process_monitor = Mock()
        mock_process_monitor.get_redis_processes = AsyncMock(return_value=[])

        pid = await aggregator._resolve_redis_pid(mock_process_monitor)

        assert pid is None
        mock_process_monitor.get_redis_processes.assert_awaited_once()

    def test_status_data_collectors_dataclass(self):
        """Test StatusDataCollectors dataclass."""
        collectors = StatusDataCollectors(
            service_collector=Mock(),
            health_collector=Mock(),
            key_counter=Mock(),
            message_collector=Mock(),
            price_collector=Mock(),
            weather_collector=Mock(),
            log_collector=Mock(),
            tracker_collector=Mock(),
            kalshi_collector=Mock(),
        )
        assert collectors.service_collector is not None
        assert collectors.kalshi_collector is not None
        # Add more assertions for other attributes if needed
