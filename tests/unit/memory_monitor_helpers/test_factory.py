"""Tests for memory monitor factory."""

from unittest.mock import MagicMock, patch

import pytest

from src.common.memory_monitor_helpers.alert_logger import AlertLogger
from src.common.memory_monitor_helpers.collection_tracker import CollectionTracker
from src.common.memory_monitor_helpers.factory import MemoryMonitorFactory
from src.common.memory_monitor_helpers.metrics_reader import MetricsReader
from src.common.memory_monitor_helpers.monitoring_loop import MonitoringLoop
from src.common.memory_monitor_helpers.snapshot_collector import SnapshotCollector
from src.common.memory_monitor_helpers.status_formatter import StatusFormatter
from src.common.memory_monitor_helpers.trend_analyzer import TrendAnalyzer


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_returns_tuple_of_seven_elements(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    result = MemoryMonitorFactory.create_components(
        service_name="test_service",
        check_interval_seconds=60,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=10,
    )

    assert isinstance(result, tuple)
    assert len(result) == 7


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_returns_correct_types(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    (
        metrics_reader,
        collection_tracker,
        snapshot_collector,
        trend_analyzer,
        alert_logger,
        monitoring_loop,
        status_formatter,
    ) = MemoryMonitorFactory.create_components(
        service_name="test_service",
        check_interval_seconds=60,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=10,
    )

    assert isinstance(metrics_reader, MetricsReader)
    assert isinstance(collection_tracker, CollectionTracker)
    assert isinstance(snapshot_collector, SnapshotCollector)
    assert isinstance(trend_analyzer, TrendAnalyzer)
    assert isinstance(alert_logger, AlertLogger)
    assert isinstance(monitoring_loop, MonitoringLoop)
    assert isinstance(status_formatter, StatusFormatter)


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_passes_service_name_to_alert_logger(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    (
        _,
        _,
        _,
        _,
        alert_logger,
        _,
        _,
    ) = MemoryMonitorFactory.create_components(
        service_name="my_service",
        check_interval_seconds=60,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=10,
    )

    assert alert_logger.service_name == "my_service"


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_passes_check_interval_to_monitoring_loop(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    (
        _,
        _,
        _,
        _,
        _,
        monitoring_loop,
        _,
    ) = MemoryMonitorFactory.create_components(
        service_name="test_service",
        check_interval_seconds=120,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=10,
    )

    assert monitoring_loop.check_interval_seconds == 120


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_passes_max_snapshots_to_snapshot_collector(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    (
        _,
        _,
        snapshot_collector,
        _,
        _,
        _,
        _,
    ) = MemoryMonitorFactory.create_components(
        service_name="test_service",
        check_interval_seconds=60,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=15,
    )

    assert snapshot_collector.max_snapshots == 15


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_creates_psutil_process(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    MemoryMonitorFactory.create_components(
        service_name="test_service",
        check_interval_seconds=60,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=10,
    )

    mock_process_class.assert_called_once()


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_wires_metrics_reader_to_snapshot_collector(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    (
        metrics_reader,
        _,
        snapshot_collector,
        _,
        _,
        _,
        _,
    ) = MemoryMonitorFactory.create_components(
        service_name="test_service",
        check_interval_seconds=60,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=10,
    )

    assert snapshot_collector.metrics_reader is metrics_reader


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_wires_collection_tracker_to_snapshot_collector(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    (
        _,
        collection_tracker,
        snapshot_collector,
        _,
        _,
        _,
        _,
    ) = MemoryMonitorFactory.create_components(
        service_name="test_service",
        check_interval_seconds=60,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=10,
    )

    assert snapshot_collector.collection_tracker is collection_tracker


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_wires_snapshot_collector_to_monitoring_loop(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    (
        _,
        _,
        snapshot_collector,
        _,
        _,
        monitoring_loop,
        _,
    ) = MemoryMonitorFactory.create_components(
        service_name="test_service",
        check_interval_seconds=60,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=10,
    )

    assert monitoring_loop.snapshot_collector is snapshot_collector


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_wires_trend_analyzer_to_monitoring_loop(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    (
        _,
        _,
        _,
        trend_analyzer,
        _,
        monitoring_loop,
        _,
    ) = MemoryMonitorFactory.create_components(
        service_name="test_service",
        check_interval_seconds=60,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=10,
    )

    assert monitoring_loop.trend_analyzer is trend_analyzer


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_wires_alert_logger_to_monitoring_loop(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    (
        _,
        _,
        _,
        _,
        alert_logger,
        monitoring_loop,
        _,
    ) = MemoryMonitorFactory.create_components(
        service_name="test_service",
        check_interval_seconds=60,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=10,
    )

    assert monitoring_loop.alert_logger is alert_logger


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_wires_service_name_to_status_formatter(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    (
        _,
        _,
        _,
        _,
        _,
        _,
        status_formatter,
    ) = MemoryMonitorFactory.create_components(
        service_name="my_service",
        check_interval_seconds=60,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=10,
    )

    assert status_formatter.service_name == "my_service"


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_wires_snapshot_collector_to_status_formatter(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    (
        _,
        _,
        snapshot_collector,
        _,
        _,
        _,
        status_formatter,
    ) = MemoryMonitorFactory.create_components(
        service_name="test_service",
        check_interval_seconds=60,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=10,
    )

    assert status_formatter.snapshot_collector is snapshot_collector


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_wires_collection_tracker_to_status_formatter(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    (
        _,
        collection_tracker,
        _,
        _,
        _,
        _,
        status_formatter,
    ) = MemoryMonitorFactory.create_components(
        service_name="test_service",
        check_interval_seconds=60,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=10,
    )

    assert status_formatter.collection_tracker is collection_tracker


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_wires_monitoring_loop_to_status_formatter(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    (
        _,
        _,
        _,
        _,
        _,
        monitoring_loop,
        status_formatter,
    ) = MemoryMonitorFactory.create_components(
        service_name="test_service",
        check_interval_seconds=60,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=10,
    )

    assert status_formatter.monitoring_loop is monitoring_loop


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_passes_thresholds_to_trend_analyzer(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    (
        _,
        _,
        _,
        trend_analyzer,
        _,
        _,
        _,
    ) = MemoryMonitorFactory.create_components(
        service_name="test_service",
        check_interval_seconds=75,
        memory_growth_threshold_mb=100.5,
        collection_growth_threshold=250,
        task_count_threshold=300,
        max_snapshots=10,
    )

    assert trend_analyzer.memory_growth_threshold_mb == pytest.approx(100.5)
    assert trend_analyzer.collection_growth_threshold == 250
    assert trend_analyzer.task_count_threshold == 300
    assert trend_analyzer.check_interval_seconds == 75


@patch("src.common.memory_monitor_helpers.factory.psutil.Process")
def test_create_components_passes_process_to_metrics_reader(mock_process_class):
    mock_process = MagicMock()
    mock_process_class.return_value = mock_process

    (
        metrics_reader,
        _,
        _,
        _,
        _,
        _,
        _,
    ) = MemoryMonitorFactory.create_components(
        service_name="test_service",
        check_interval_seconds=60,
        memory_growth_threshold_mb=50.0,
        collection_growth_threshold=100,
        task_count_threshold=200,
        max_snapshots=10,
    )

    assert metrics_reader.process is mock_process
