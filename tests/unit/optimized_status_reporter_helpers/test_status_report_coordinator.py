"""Comprehensive unit tests for StatusReportCoordinator and related classes."""

import asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import RedisError

from common.optimized_status_reporter_helpers.status_report_coordinator import (
    ConsolePrinter,
    DataGatherer,
    DataGathererCollectors,
    StatusDictData,
    StatusReportCoordinator,
    StatusReportCoordinatorCollectors,
    StatusReportCoordinatorConfig,
    _build_status_dict,
)
from common.redis_utils import RedisOperationError


@pytest.fixture
def mock_collectors():
    """Create mock collectors for testing."""
    return DataGathererCollectors(
        redis_key_counter=AsyncMock(),
        price_data_collector=AsyncMock(),
        weather_temp_collector=AsyncMock(),
        message_metrics_collector=AsyncMock(),
        service_state_collector=AsyncMock(),
        tracker_status_collector=AsyncMock(),
        health_snapshot_collector=AsyncMock(),
        log_activity_collector=AsyncMock(),
        kalshi_market_status_collector=AsyncMock(),
    )


@pytest.fixture
def mock_coordinator_collectors():
    """Create coordinator collectors for testing."""
    return StatusReportCoordinatorCollectors(
        redis_key_counter=AsyncMock(),
        price_data_collector=AsyncMock(),
        weather_temp_collector=AsyncMock(),
        realtime_metrics_collector=AsyncMock(),
        message_metrics_collector=AsyncMock(),
        service_state_collector=AsyncMock(),
        tracker_status_collector=AsyncMock(),
        health_snapshot_collector=AsyncMock(),
        log_activity_collector=AsyncMock(),
        kalshi_market_status_collector=AsyncMock(),
    )


@pytest.fixture
def mock_console_printer():
    """Create mock console section printer."""
    printer = MagicMock()
    printer._emit_status_line = MagicMock()
    printer.print_exchange_info = MagicMock()
    printer.print_price_info = MagicMock()
    printer.print_weather_section = MagicMock()
    printer.print_managed_services = MagicMock(return_value=(5, 8))
    printer.print_monitor_service = MagicMock()
    printer.print_redis_health_section = MagicMock()
    printer.print_system_resources_section = MagicMock()
    printer.print_message_metrics_section = MagicMock()
    printer.print_weather_metrics_section = MagicMock()
    printer.print_tracker_status_section = MagicMock()
    return printer


@pytest.fixture
def mock_weather_section_generator():
    """Create mock weather section generator."""
    generator = MagicMock()
    generator.generate_weather_section = MagicMock(return_value=["Weather line 1"])
    return generator


@pytest.fixture
def mock_data_coercion():
    """Create mock data coercion utility."""
    coercion = MagicMock()
    coercion.coerce_mapping = MagicMock(side_effect=lambda x: x or {})
    return coercion


@pytest.fixture
def sample_status_dict_data():
    """Create sample status dict data."""
    return StatusDictData(
        redis_pid=12345,
        running_services={"kalshi": "ready", "tracker": "ready"},
        health_snapshot={
            "redis_connection_healthy": True,
            "health_checks": {},
            "system_resources_health": {},
            "redis_health_check": {},
            "ldm_listener_health": {},
        },
        key_counts={
            "redis_deribit_keys": 100,
            "redis_kalshi_keys": 50,
            "redis_cfb_keys": 10,
            "redis_weather_keys": 25,
        },
        message_metrics={
            "deribit_messages_60s": 500,
            "kalshi_messages_60s": 200,
            "cfb_messages_60s": 50,
            "asos_messages_65m": 100,
        },
        price_data={"btc_price": 50000.0, "eth_price": 3000.0},
        weather_temperatures={"KORD": 72.5, "KJFK": 68.0},
        kalshi_market_status={"status": "open"},
        log_activity_map={"kalshi": 1234567890.0},
        stale_logs=[],
        tracker_status={"active": True},
    )


class TestDataGathererInitialization:
    """Test DataGatherer initialization."""

    def test_initialization_sets_collectors(self, mock_collectors):
        """Verify DataGatherer initializes with all collectors."""
        gatherer = DataGatherer(mock_collectors)

        assert gatherer.redis_key_counter is not None
        assert gatherer.price_data_collector is not None
        assert gatherer.weather_temp_collector is not None
        assert gatherer.message_metrics_collector is not None
        assert gatherer.service_state_collector is not None
        assert gatherer.tracker_status_collector is not None
        assert gatherer.health_snapshot_collector is not None
        assert gatherer.log_activity_collector is not None
        assert gatherer.kalshi_market_status_collector is not None


class TestDataGathererGatherAllStatusData:
    """Test DataGatherer.gather_all_status_data method."""

    @pytest.mark.asyncio
    async def test_gathers_all_data_sources(self, mock_collectors):
        """Test that all data sources are collected."""
        gatherer = DataGatherer(mock_collectors)
        mock_redis = AsyncMock()

        mock_collectors.service_state_collector.collect_running_services.return_value = {"kalshi": "ready"}
        mock_collectors.service_state_collector.resolve_redis_pid.return_value = 12345
        mock_collectors.health_snapshot_collector.collect_health_snapshot.return_value = {
            "redis_connection_healthy": True,
            "health_checks": {},
            "system_resources_health": {},
            "redis_health_check": {},
            "ldm_listener_health": {},
        }
        mock_collectors.redis_key_counter.collect_key_counts.return_value = {
            "redis_deribit_keys": 100,
            "redis_kalshi_keys": 50,
            "redis_cfb_keys": 10,
            "redis_weather_keys": 25,
        }
        mock_collectors.message_metrics_collector.collect_message_metrics.return_value = {
            "deribit_messages_60s": 500,
            "kalshi_messages_60s": 200,
            "cfb_messages_60s": 50,
            "asos_messages_65m": 100,
        }
        mock_collectors.price_data_collector.collect_price_data.return_value = {
            "btc_price": 50000.0,
            "eth_price": 3000.0,
        }
        mock_collectors.weather_temp_collector.collect_weather_temperatures.return_value = {"KORD": 72.5}
        mock_collectors.kalshi_market_status_collector.get_kalshi_market_status.return_value = {"status": "open"}
        mock_collectors.log_activity_collector.collect_log_activity_map.return_value = (
            {"kalshi": 1234567890.0},
            [],
        )
        mock_collectors.tracker_status_collector.collect_tracker_status.return_value = {"active": True}
        # merge_tracker_service_state is NOT async, so use regular Mock
        mock_collectors.tracker_status_collector.merge_tracker_service_state = MagicMock(
            return_value={
                "kalshi": "ready",
                "tracker": "ready",
            }
        )

        mock_process_monitor = AsyncMock()

        async def mock_get_monitor():
            return mock_process_monitor

        with patch("common.process_monitor.get_global_process_monitor", side_effect=mock_get_monitor):
            result = await gatherer.gather_all_status_data(mock_redis)

            assert result["redis_process"]["pid"] == 12345
            assert result["running_services"]["kalshi"] == "ready"
            assert result["btc_price"] == 50000.0
            assert result["weather_temperatures"]["KORD"] == 72.5

    @pytest.mark.asyncio
    async def test_calls_all_collectors(self, mock_collectors):
        """Test that all collectors are called."""
        gatherer = DataGatherer(mock_collectors)
        mock_redis = AsyncMock()

        mock_collectors.service_state_collector.collect_running_services.return_value = {}
        mock_collectors.service_state_collector.resolve_redis_pid.return_value = 0
        mock_collectors.health_snapshot_collector.collect_health_snapshot.return_value = {
            "redis_connection_healthy": True,
            "health_checks": {},
            "system_resources_health": {},
            "redis_health_check": {},
            "ldm_listener_health": {},
        }
        mock_collectors.redis_key_counter.collect_key_counts.return_value = {
            "redis_deribit_keys": 0,
            "redis_kalshi_keys": 0,
            "redis_cfb_keys": 0,
            "redis_weather_keys": 0,
        }
        mock_collectors.message_metrics_collector.collect_message_metrics.return_value = {
            "deribit_messages_60s": 0,
            "kalshi_messages_60s": 0,
            "cfb_messages_60s": 0,
            "asos_messages_65m": 0,
        }
        mock_collectors.price_data_collector.collect_price_data.return_value = {
            "btc_price": 0.0,
            "eth_price": 0.0,
        }
        mock_collectors.weather_temp_collector.collect_weather_temperatures.return_value = {}
        mock_collectors.kalshi_market_status_collector.get_kalshi_market_status.return_value = {}
        mock_collectors.log_activity_collector.collect_log_activity_map.return_value = ({}, [])
        mock_collectors.tracker_status_collector.collect_tracker_status.return_value = {}
        # merge_tracker_service_state is NOT async, so use regular Mock
        mock_collectors.tracker_status_collector.merge_tracker_service_state = MagicMock(return_value={})

        mock_process_monitor = AsyncMock()

        async def mock_get_monitor():
            return mock_process_monitor

        with patch("common.process_monitor.get_global_process_monitor", side_effect=mock_get_monitor):
            await gatherer.gather_all_status_data(mock_redis)

            mock_collectors.redis_key_counter.collect_key_counts.assert_called_once()
            mock_collectors.price_data_collector.collect_price_data.assert_called_once()
            mock_collectors.weather_temp_collector.collect_weather_temperatures.assert_called_once()
            mock_collectors.message_metrics_collector.collect_message_metrics.assert_called_once()
            mock_collectors.health_snapshot_collector.collect_health_snapshot.assert_called_once()
            mock_collectors.log_activity_collector.collect_log_activity_map.assert_called_once()


class TestBuildStatusDict:
    """Test _build_status_dict function."""

    def test_builds_complete_status_dict(self, sample_status_dict_data):
        """Test that status dict is built with all required fields."""
        result = _build_status_dict(sample_status_dict_data)

        assert result["redis_process"]["pid"] == 12345
        assert result["running_services"] == {"kalshi": "ready", "tracker": "ready"}
        assert result["redis_connection_healthy"] is True
        assert result["redis_deribit_keys"] == 100
        assert result["redis_kalshi_keys"] == 50
        assert result["redis_cfb_keys"] == 10
        assert result["redis_weather_keys"] == 25
        assert result["deribit_messages_60s"] == 500
        assert result["kalshi_messages_60s"] == 200
        assert result["cfb_messages_60s"] == 50
        assert result["asos_messages_65m"] == 100
        assert result["weather_temperatures"] == {"KORD": 72.5, "KJFK": 68.0}
        assert result["stale_logs"] == []
        assert result["log_activity"] == {"kalshi": 1234567890.0}
        assert result["btc_price"] == 50000.0
        assert result["eth_price"] == 3000.0
        assert result["kalshi_market_status"] == {"status": "open"}
        assert result["tracker_status"] == {"active": True}

    def test_extracts_nested_health_data(self, sample_status_dict_data):
        """Test that nested health snapshot data is extracted correctly."""
        result = _build_status_dict(sample_status_dict_data)

        assert "health_checks" in result
        assert "system_resources_health" in result
        assert "redis_health_check" in result
        assert "ldm_listener_health" in result


class TestConsolePrinterInitialization:
    """Test ConsolePrinter initialization."""

    def test_initialization_sets_dependencies(self, mock_console_printer, mock_weather_section_generator, mock_data_coercion):
        """Verify ConsolePrinter initializes with dependencies."""
        printer = ConsolePrinter(mock_console_printer, mock_weather_section_generator, mock_data_coercion)

        assert printer.console_section_printer is not None
        assert printer.weather_section_generator is not None
        assert printer.data_coercion is not None


class TestConsolePrinterPrintFullStatus:
    """Test ConsolePrinter.print_full_status method."""

    @pytest.mark.asyncio
    async def test_prints_all_sections(self, mock_console_printer, mock_weather_section_generator, mock_data_coercion):
        """Test that all status sections are printed."""
        printer = ConsolePrinter(mock_console_printer, mock_weather_section_generator, mock_data_coercion)

        status_data = {
            "kalshi_market_status": {"status": "open"},
            "btc_price": 50000.0,
            "eth_price": 3000.0,
            "weather_temperatures": {"KORD": 72.5},
            "tracker_status": {"active": True},
            "log_activity": {},
            "system_resources_health": {},
        }

        with patch("common.optimized_status_reporter_helpers.status_report_coordinator.get_current_utc") as mock_time:
            mock_time.return_value.strftime.return_value = "2025-01-01 12:00:00"
            await printer.print_full_status(status_data)

            mock_console_printer._emit_status_line.assert_called()
            mock_console_printer.print_exchange_info.assert_called_once()
            mock_console_printer.print_price_info.assert_called_once_with(50000.0, 3000.0)
            mock_console_printer.print_weather_section.assert_called_once()
            mock_console_printer.print_managed_services.assert_called_once()
            mock_console_printer.print_monitor_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_missing_data_gracefully(self, mock_console_printer, mock_weather_section_generator, mock_data_coercion):
        """Test that missing data fields are handled gracefully."""
        printer = ConsolePrinter(mock_console_printer, mock_weather_section_generator, mock_data_coercion)

        status_data = {
            "system_resources_health": {},
            "tracker_status": {},
            "log_activity": {},
        }

        with patch("common.optimized_status_reporter_helpers.status_report_coordinator.get_current_utc") as mock_time:
            mock_time.return_value.strftime.return_value = "2025-01-01 12:00:00"
            await printer.print_full_status(status_data)

            mock_console_printer.print_exchange_info.assert_called_once()
            mock_console_printer.print_price_info.assert_called_once_with(None, None)

    @pytest.mark.asyncio
    async def test_coerces_data_before_printing(self, mock_console_printer, mock_weather_section_generator, mock_data_coercion):
        """Test that data is coerced using data_coercion utility."""
        printer = ConsolePrinter(mock_console_printer, mock_weather_section_generator, mock_data_coercion)

        status_data = {
            "kalshi_market_status": {"status": "open"},
            "weather_temperatures": {"KORD": 72.5},
            "tracker_status": {"active": True},
            "log_activity": {},
            "system_resources_health": {},
        }

        with patch("common.optimized_status_reporter_helpers.status_report_coordinator.get_current_utc") as mock_time:
            mock_time.return_value.strftime.return_value = "2025-01-01 12:00:00"
            await printer.print_full_status(status_data)

            assert mock_data_coercion.coerce_mapping.call_count >= 2

    @pytest.mark.asyncio
    async def test_generates_weather_section(self, mock_console_printer, mock_weather_section_generator, mock_data_coercion):
        """Test that weather section is generated."""
        printer = ConsolePrinter(mock_console_printer, mock_weather_section_generator, mock_data_coercion)

        status_data = {
            "weather_temperatures": {"KORD": 72.5},
            "tracker_status": {},
            "log_activity": {},
            "system_resources_health": {},
        }

        with patch("common.optimized_status_reporter_helpers.status_report_coordinator.get_current_utc") as mock_time:
            mock_time.return_value.strftime.return_value = "2025-01-01 12:00:00"
            await printer.print_full_status(status_data)

            mock_weather_section_generator.generate_weather_section.assert_called_once()


class TestStatusReportCoordinatorInitialization:
    """Test StatusReportCoordinator initialization."""

    def test_initialization_creates_components(self, mock_coordinator_collectors):
        """Verify StatusReportCoordinator creates all components."""
        config = StatusReportCoordinatorConfig(
            process_manager=MagicMock(),
            health_checker=MagicMock(),
            metadata_store=MagicMock(),
            tracker_controller=MagicMock(),
            collectors=mock_coordinator_collectors,
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        coordinator = StatusReportCoordinator(config)

        assert coordinator.process_manager is not None
        assert coordinator.health_checker is not None
        assert coordinator.metadata_store is not None
        assert coordinator.tracker_controller is not None
        assert coordinator.data_gatherer is not None
        assert coordinator.console_printer is not None

    def test_initialization_creates_data_gatherer_collectors(self, mock_coordinator_collectors):
        """Test that DataGatherer is initialized with correct collectors."""
        config = StatusReportCoordinatorConfig(
            process_manager=MagicMock(),
            health_checker=MagicMock(),
            metadata_store=MagicMock(),
            tracker_controller=MagicMock(),
            collectors=mock_coordinator_collectors,
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        coordinator = StatusReportCoordinator(config)

        assert coordinator.data_gatherer.redis_key_counter is not None
        assert coordinator.data_gatherer.price_data_collector is not None


class TestStatusReportCoordinatorGenerateAndStreamStatusReport:
    """Test StatusReportCoordinator.generate_and_stream_status_report method."""

    @pytest.mark.asyncio
    async def test_generates_and_streams_report(self, mock_coordinator_collectors):
        """Test that status report is generated and streamed."""
        config = StatusReportCoordinatorConfig(
            process_manager=MagicMock(),
            health_checker=MagicMock(),
            metadata_store=MagicMock(),
            tracker_controller=MagicMock(),
            collectors=mock_coordinator_collectors,
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        coordinator = StatusReportCoordinator(config)

        mock_status_data = {
            "redis_process": {"pid": 12345},
            "running_services": {},
            "btc_price": 50000.0,
        }

        with patch("common.redis_protocol.connection_pool_core.get_redis_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            with patch.object(coordinator.data_gatherer, "gather_all_status_data", return_value=mock_status_data) as mock_gather:
                with patch.object(coordinator.console_printer, "print_full_status") as mock_print:
                    result = await coordinator.generate_and_stream_status_report()

                    mock_gather.assert_called_once_with(mock_client)
                    mock_print.assert_called_once_with(mock_status_data)
                    assert result == mock_status_data

    @pytest.mark.asyncio
    async def test_propagates_redis_errors(self, mock_coordinator_collectors):
        """Test that Redis errors are caught and re-raised as RuntimeError."""
        config = StatusReportCoordinatorConfig(
            process_manager=MagicMock(),
            health_checker=MagicMock(),
            metadata_store=MagicMock(),
            tracker_controller=MagicMock(),
            collectors=mock_coordinator_collectors,
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        coordinator = StatusReportCoordinator(config)

        with patch("common.redis_protocol.connection_pool_core.get_redis_client") as mock_get_client:
            mock_get_client.side_effect = RedisError("Connection failed")

            with pytest.raises(RuntimeError, match="Status report generation failed"):
                await coordinator.generate_and_stream_status_report()

    @pytest.mark.asyncio
    async def test_handles_redis_operation_error(self, mock_coordinator_collectors):
        """Test that RedisOperationError is caught and re-raised."""
        config = StatusReportCoordinatorConfig(
            process_manager=MagicMock(),
            health_checker=MagicMock(),
            metadata_store=MagicMock(),
            tracker_controller=MagicMock(),
            collectors=mock_coordinator_collectors,
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        coordinator = StatusReportCoordinator(config)

        with patch("common.redis_protocol.connection_pool_core.get_redis_client") as mock_get_client:
            mock_get_client.side_effect = RedisOperationError("Operation failed")

            with pytest.raises(RuntimeError, match="Status report generation failed"):
                await coordinator.generate_and_stream_status_report()

    @pytest.mark.asyncio
    async def test_handles_connection_error(self, mock_coordinator_collectors):
        """Test that ConnectionError is caught and re-raised."""
        config = StatusReportCoordinatorConfig(
            process_manager=MagicMock(),
            health_checker=MagicMock(),
            metadata_store=MagicMock(),
            tracker_controller=MagicMock(),
            collectors=mock_coordinator_collectors,
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        coordinator = StatusReportCoordinator(config)

        with patch("common.redis_protocol.connection_pool_core.get_redis_client") as mock_get_client:
            mock_get_client.side_effect = ConnectionError("Network error")

            with pytest.raises(RuntimeError, match="Status report generation failed"):
                await coordinator.generate_and_stream_status_report()

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self, mock_coordinator_collectors):
        """Test that TimeoutError is caught and re-raised."""
        config = StatusReportCoordinatorConfig(
            process_manager=MagicMock(),
            health_checker=MagicMock(),
            metadata_store=MagicMock(),
            tracker_controller=MagicMock(),
            collectors=mock_coordinator_collectors,
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        coordinator = StatusReportCoordinator(config)

        with patch("common.redis_protocol.connection_pool_core.get_redis_client") as mock_get_client:
            mock_get_client.side_effect = TimeoutError("Request timeout")

            with pytest.raises(RuntimeError, match="Status report generation failed"):
                await coordinator.generate_and_stream_status_report()

    @pytest.mark.asyncio
    async def test_handles_asyncio_timeout_error(self, mock_coordinator_collectors):
        """Test that asyncio.TimeoutError is caught and re-raised."""
        config = StatusReportCoordinatorConfig(
            process_manager=MagicMock(),
            health_checker=MagicMock(),
            metadata_store=MagicMock(),
            tracker_controller=MagicMock(),
            collectors=mock_coordinator_collectors,
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        coordinator = StatusReportCoordinator(config)

        with patch("common.redis_protocol.connection_pool_core.get_redis_client") as mock_get_client:
            mock_get_client.side_effect = asyncio.TimeoutError("Async timeout")

            with pytest.raises(RuntimeError, match="Status report generation failed"):
                await coordinator.generate_and_stream_status_report()

    @pytest.mark.asyncio
    async def test_handles_runtime_error(self, mock_coordinator_collectors):
        """Test that RuntimeError is caught and re-raised."""
        config = StatusReportCoordinatorConfig(
            process_manager=MagicMock(),
            health_checker=MagicMock(),
            metadata_store=MagicMock(),
            tracker_controller=MagicMock(),
            collectors=mock_coordinator_collectors,
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        coordinator = StatusReportCoordinator(config)

        with patch("common.redis_protocol.connection_pool_core.get_redis_client") as mock_get_client:
            mock_get_client.side_effect = RuntimeError("Runtime error")

            with pytest.raises(RuntimeError, match="Status report generation failed"):
                await coordinator.generate_and_stream_status_report()

    @pytest.mark.asyncio
    async def test_handles_value_error(self, mock_coordinator_collectors):
        """Test that ValueError is caught and re-raised."""
        config = StatusReportCoordinatorConfig(
            process_manager=MagicMock(),
            health_checker=MagicMock(),
            metadata_store=MagicMock(),
            tracker_controller=MagicMock(),
            collectors=mock_coordinator_collectors,
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        coordinator = StatusReportCoordinator(config)

        with patch("common.redis_protocol.connection_pool_core.get_redis_client") as mock_get_client:
            mock_get_client.side_effect = ValueError("Invalid value")

            with pytest.raises(RuntimeError, match="Status report generation failed"):
                await coordinator.generate_and_stream_status_report()

    @pytest.mark.asyncio
    async def test_handles_import_error(self, mock_coordinator_collectors):
        """Test that ImportError is caught and re-raised."""
        config = StatusReportCoordinatorConfig(
            process_manager=MagicMock(),
            health_checker=MagicMock(),
            metadata_store=MagicMock(),
            tracker_controller=MagicMock(),
            collectors=mock_coordinator_collectors,
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        coordinator = StatusReportCoordinator(config)

        with patch("common.redis_protocol.connection_pool_core.get_redis_client") as mock_get_client:
            mock_get_client.side_effect = ImportError("Module not found")

            with pytest.raises(RuntimeError, match="Status report generation failed"):
                await coordinator.generate_and_stream_status_report()

    @pytest.mark.asyncio
    async def test_logs_exception_on_error(self, mock_coordinator_collectors):
        """Test that exceptions are logged before re-raising."""
        config = StatusReportCoordinatorConfig(
            process_manager=MagicMock(),
            health_checker=MagicMock(),
            metadata_store=MagicMock(),
            tracker_controller=MagicMock(),
            collectors=mock_coordinator_collectors,
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        coordinator = StatusReportCoordinator(config)

        with patch("common.redis_protocol.connection_pool_core.get_redis_client") as mock_get_client:
            mock_get_client.side_effect = RedisError("Test error")

            with patch("common.optimized_status_reporter_helpers.status_report_coordinator.logger") as mock_logger:
                with pytest.raises(RuntimeError):
                    await coordinator.generate_and_stream_status_report()

                mock_logger.exception.assert_called_once()


class TestDataGathererCollectorsDataclass:
    """Test DataGathererCollectors dataclass."""

    def test_is_frozen(self, mock_collectors):
        """Verify DataGathererCollectors is frozen (immutable)."""
        with pytest.raises(AttributeError):
            mock_collectors.redis_key_counter = AsyncMock()


class TestStatusDictDataDataclass:
    """Test StatusDictData dataclass."""

    def test_is_frozen(self, sample_status_dict_data):
        """Verify StatusDictData is frozen (immutable)."""
        with pytest.raises(AttributeError):
            sample_status_dict_data.redis_pid = 99999


class TestStatusReportCoordinatorCollectorsDataclass:
    """Test StatusReportCoordinatorCollectors dataclass."""

    def test_is_frozen(self, mock_coordinator_collectors):
        """Verify StatusReportCoordinatorCollectors is frozen (immutable)."""
        with pytest.raises(AttributeError):
            mock_coordinator_collectors.redis_key_counter = AsyncMock()


class TestStatusReportCoordinatorConfigDataclass:
    """Test StatusReportCoordinatorConfig dataclass."""

    def test_is_frozen(self, mock_coordinator_collectors):
        """Verify StatusReportCoordinatorConfig is frozen (immutable)."""
        config = StatusReportCoordinatorConfig(
            process_manager=MagicMock(),
            health_checker=MagicMock(),
            metadata_store=MagicMock(),
            tracker_controller=MagicMock(),
            collectors=mock_coordinator_collectors,
            console_section_printer=MagicMock(),
            weather_section_generator=MagicMock(),
            data_coercion=MagicMock(),
        )

        with pytest.raises(AttributeError):
            config.process_manager = MagicMock()
