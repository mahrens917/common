"""Tests for memory monitor snapshot collector."""

from unittest.mock import MagicMock

import pytest

from src.common.memory_monitor_helpers.snapshot_collector import (
    MemorySnapshot,
    SnapshotCollector,
)


@pytest.fixture
def mock_metrics_reader():
    """Create a mock metrics reader."""
    reader = MagicMock()
    reader.get_current_memory_usage.return_value = 100.0
    reader.get_system_memory_percent.return_value = 45.0
    reader.get_current_task_count.return_value = 5
    return reader


@pytest.fixture
def mock_collection_tracker():
    """Create a mock collection tracker."""
    tracker = MagicMock()
    tracker.get_collection_sizes.return_value = {"queue": 10, "cache": 20}
    return tracker


@pytest.fixture
def snapshot_collector(mock_metrics_reader, mock_collection_tracker):
    """Create a snapshot collector with mocked dependencies."""
    return SnapshotCollector(
        metrics_reader=mock_metrics_reader,
        collection_tracker=mock_collection_tracker,
        max_snapshots=5,
    )


def test_memory_snapshot_dataclass_creation():
    """Test MemorySnapshot dataclass can be created with all fields."""
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=100.0,
        system_memory_percent=50.0,
        collection_sizes={"queue": 10},
        task_count=5,
    )

    assert snapshot.timestamp == 1234567890.0
    assert snapshot.process_memory_mb == 100.0
    assert snapshot.system_memory_percent == 50.0
    assert snapshot.collection_sizes == {"queue": 10}
    assert snapshot.task_count == 5


def test_init_sets_attributes(mock_metrics_reader, mock_collection_tracker):
    """Test initialization sets all attributes correctly."""
    collector = SnapshotCollector(
        metrics_reader=mock_metrics_reader,
        collection_tracker=mock_collection_tracker,
        max_snapshots=10,
    )

    assert collector.metrics_reader is mock_metrics_reader
    assert collector.collection_tracker is mock_collection_tracker
    assert collector.max_snapshots == 10
    assert collector.snapshots == []


def test_take_snapshot_returns_memory_snapshot(
    snapshot_collector, mock_metrics_reader, mock_collection_tracker
):
    """Test take_snapshot returns a MemorySnapshot instance."""
    result = snapshot_collector.take_snapshot()

    assert isinstance(result, MemorySnapshot)
    assert result.process_memory_mb == 100.0
    assert result.system_memory_percent == 45.0
    assert result.collection_sizes == {"queue": 10, "cache": 20}
    assert result.task_count == 5
    assert result.timestamp > 0


def test_take_snapshot_calls_metrics_reader_methods(snapshot_collector, mock_metrics_reader):
    """Test take_snapshot calls all metrics reader methods."""
    snapshot_collector.take_snapshot()

    mock_metrics_reader.get_current_memory_usage.assert_called_once()
    mock_metrics_reader.get_system_memory_percent.assert_called_once()
    mock_metrics_reader.get_current_task_count.assert_called_once()


def test_take_snapshot_calls_collection_tracker(snapshot_collector, mock_collection_tracker):
    """Test take_snapshot calls collection tracker."""
    snapshot_collector.take_snapshot()

    mock_collection_tracker.get_collection_sizes.assert_called_once()


def test_take_snapshot_stores_snapshot(snapshot_collector):
    """Test take_snapshot stores the snapshot in the list."""
    assert len(snapshot_collector.snapshots) == 0

    snapshot_collector.take_snapshot()

    assert len(snapshot_collector.snapshots) == 1


def test_take_snapshot_respects_max_snapshots(snapshot_collector):
    """Test take_snapshot respects max_snapshots limit."""
    # Take 7 snapshots (max is 5)
    for _ in range(7):
        snapshot_collector.take_snapshot()

    assert len(snapshot_collector.snapshots) == 5


def test_take_snapshot_removes_oldest_when_exceeding_max(snapshot_collector, mock_metrics_reader):
    """Test take_snapshot removes oldest snapshot when exceeding max."""
    # Take snapshots with different memory values to identify them
    for i in range(7):
        mock_metrics_reader.get_current_memory_usage.return_value = float(i)
        snapshot_collector.take_snapshot()

    # Should have removed first 2 snapshots (0 and 1)
    assert len(snapshot_collector.snapshots) == 5
    assert snapshot_collector.snapshots[0].process_memory_mb == 2.0
    assert snapshot_collector.snapshots[-1].process_memory_mb == 6.0


def test_take_snapshot_with_overrides_uses_default_task_count(
    snapshot_collector, mock_metrics_reader
):
    """Test take_snapshot_with_overrides uses default task count when no supplier provided."""
    result = snapshot_collector.take_snapshot_with_overrides()

    assert result.task_count == 5
    mock_metrics_reader.get_current_task_count.assert_called_once()


def test_take_snapshot_with_overrides_uses_custom_task_count_supplier(
    snapshot_collector, mock_metrics_reader
):
    """Test take_snapshot_with_overrides uses custom task count supplier."""
    custom_supplier = MagicMock(return_value=42)

    result = snapshot_collector.take_snapshot_with_overrides(task_count_supplier=custom_supplier)

    assert result.task_count == 42
    custom_supplier.assert_called_once()
    mock_metrics_reader.get_current_task_count.assert_not_called()


def test_take_snapshot_with_overrides_stores_snapshot(snapshot_collector):
    """Test take_snapshot_with_overrides stores the snapshot."""
    assert len(snapshot_collector.snapshots) == 0

    snapshot_collector.take_snapshot_with_overrides()

    assert len(snapshot_collector.snapshots) == 1


def test_take_snapshot_with_overrides_returns_same_as_take_snapshot(snapshot_collector):
    """Test take_snapshot_with_overrides returns same type as take_snapshot."""
    result1 = snapshot_collector.take_snapshot()
    result2 = snapshot_collector.take_snapshot_with_overrides()

    assert isinstance(result1, MemorySnapshot)
    assert isinstance(result2, MemorySnapshot)


def test_get_snapshots_returns_empty_list_initially(snapshot_collector):
    """Test get_snapshots returns empty list when no snapshots taken."""
    result = snapshot_collector.get_snapshots()

    assert result == []


def test_get_snapshots_returns_all_snapshots(snapshot_collector):
    """Test get_snapshots returns all stored snapshots."""
    snapshot_collector.take_snapshot()
    snapshot_collector.take_snapshot()
    snapshot_collector.take_snapshot()

    result = snapshot_collector.get_snapshots()

    assert len(result) == 3
    assert all(isinstance(s, MemorySnapshot) for s in result)


def test_get_snapshots_returns_actual_list_reference(snapshot_collector):
    """Test get_snapshots returns the actual list (not a copy)."""
    snapshot_collector.take_snapshot()

    result = snapshot_collector.get_snapshots()

    assert result is snapshot_collector.snapshots


def test_get_latest_snapshot_returns_none_when_empty(snapshot_collector):
    """Test get_latest_snapshot returns None when no snapshots exist."""
    result = snapshot_collector.get_latest_snapshot()

    assert result is None


def test_get_latest_snapshot_returns_most_recent(snapshot_collector, mock_metrics_reader):
    """Test get_latest_snapshot returns the most recent snapshot."""
    # Take multiple snapshots with different memory values
    for i in range(3):
        mock_metrics_reader.get_current_memory_usage.return_value = float(i)
        snapshot_collector.take_snapshot()

    result = snapshot_collector.get_latest_snapshot()

    assert result is not None
    assert result.process_memory_mb == 2.0


def test_get_latest_snapshot_returns_actual_snapshot_reference(snapshot_collector):
    """Test get_latest_snapshot returns the actual snapshot (not a copy)."""
    snapshot_collector.take_snapshot()

    result = snapshot_collector.get_latest_snapshot()

    assert result is snapshot_collector.snapshots[-1]


def test_take_snapshot_with_zero_max_snapshots(mock_metrics_reader, mock_collection_tracker):
    """Test behavior with max_snapshots set to 0."""
    collector = SnapshotCollector(
        metrics_reader=mock_metrics_reader,
        collection_tracker=mock_collection_tracker,
        max_snapshots=0,
    )

    collector.take_snapshot()

    # Should have no snapshots since max is 0
    assert len(collector.snapshots) == 0


def test_take_snapshot_with_one_max_snapshot(mock_metrics_reader, mock_collection_tracker):
    """Test behavior with max_snapshots set to 1."""
    collector = SnapshotCollector(
        metrics_reader=mock_metrics_reader,
        collection_tracker=mock_collection_tracker,
        max_snapshots=1,
    )

    # Take multiple snapshots
    for i in range(3):
        mock_metrics_reader.get_current_memory_usage.return_value = float(i)
        collector.take_snapshot()

    # Should only keep the latest one
    assert len(collector.snapshots) == 1
    assert collector.snapshots[0].process_memory_mb == 2.0


def test_snapshot_timestamp_increases_monotonically(snapshot_collector, monkeypatch):
    """Test that snapshot timestamps increase monotonically."""
    import time

    timestamps = [1000.0, 1001.0, 1002.0]
    call_count = [0]

    def mock_time():
        result = timestamps[call_count[0]]
        call_count[0] += 1
        return result

    monkeypatch.setattr(time, "time", mock_time)

    snapshot1 = snapshot_collector.take_snapshot()
    snapshot2 = snapshot_collector.take_snapshot()
    snapshot3 = snapshot_collector.take_snapshot()

    assert snapshot1.timestamp == 1000.0
    assert snapshot2.timestamp == 1001.0
    assert snapshot3.timestamp == 1002.0


def test_snapshot_collection_sizes_are_independent(snapshot_collector, mock_collection_tracker):
    """Test that collection sizes are captured independently for each snapshot."""
    # First snapshot
    mock_collection_tracker.get_collection_sizes.return_value = {"queue": 10}
    snapshot1 = snapshot_collector.take_snapshot()

    # Second snapshot with different sizes
    mock_collection_tracker.get_collection_sizes.return_value = {"queue": 20}
    snapshot2 = snapshot_collector.take_snapshot()

    # Verify snapshots have different collection sizes
    assert snapshot1.collection_sizes == {"queue": 10}
    assert snapshot2.collection_sizes == {"queue": 20}


def test_empty_collection_sizes(snapshot_collector, mock_collection_tracker):
    """Test handling of empty collection sizes."""
    mock_collection_tracker.get_collection_sizes.return_value = {}

    result = snapshot_collector.take_snapshot()

    assert result.collection_sizes == {}


def test_large_collection_sizes(snapshot_collector, mock_collection_tracker):
    """Test handling of large collection size dictionary."""
    large_dict = {f"collection_{i}": i * 100 for i in range(50)}
    mock_collection_tracker.get_collection_sizes.return_value = large_dict

    result = snapshot_collector.take_snapshot()

    assert result.collection_sizes == large_dict
    assert len(result.collection_sizes) == 50


def test_negative_memory_values(snapshot_collector, mock_metrics_reader):
    """Test handling of negative memory values (edge case)."""
    mock_metrics_reader.get_current_memory_usage.return_value = -1.0
    mock_metrics_reader.get_system_memory_percent.return_value = -5.0

    result = snapshot_collector.take_snapshot()

    assert result.process_memory_mb == -1.0
    assert result.system_memory_percent == -5.0


def test_zero_task_count(snapshot_collector, mock_metrics_reader):
    """Test handling of zero task count."""
    mock_metrics_reader.get_current_task_count.return_value = 0

    result = snapshot_collector.take_snapshot()

    assert result.task_count == 0


def test_large_task_count(snapshot_collector, mock_metrics_reader):
    """Test handling of large task count."""
    mock_metrics_reader.get_current_task_count.return_value = 10000

    result = snapshot_collector.take_snapshot()

    assert result.task_count == 10000


def test_max_snapshots_boundary(mock_metrics_reader, mock_collection_tracker):
    """Test exact boundary condition at max_snapshots."""
    collector = SnapshotCollector(
        metrics_reader=mock_metrics_reader,
        collection_tracker=mock_collection_tracker,
        max_snapshots=3,
    )

    # Take exactly max_snapshots
    for _ in range(3):
        collector.take_snapshot()

    assert len(collector.snapshots) == 3

    # Take one more
    collector.take_snapshot()

    assert len(collector.snapshots) == 3


def test_multiple_calls_to_get_snapshots_return_same_list(snapshot_collector):
    """Test that multiple calls to get_snapshots return the same list reference."""
    snapshot_collector.take_snapshot()

    result1 = snapshot_collector.get_snapshots()
    result2 = snapshot_collector.get_snapshots()

    assert result1 is result2


def test_task_count_supplier_with_zero_return(snapshot_collector):
    """Test task_count_supplier that returns zero."""
    supplier = MagicMock(return_value=0)

    result = snapshot_collector.take_snapshot_with_overrides(task_count_supplier=supplier)

    assert result.task_count == 0


def test_task_count_supplier_with_none_uses_default(snapshot_collector, mock_metrics_reader):
    """Test that passing None for task_count_supplier uses default."""
    result = snapshot_collector.take_snapshot_with_overrides(task_count_supplier=None)

    assert result.task_count == 5
    mock_metrics_reader.get_current_task_count.assert_called_once()


def test_snapshot_fields_are_set_from_correct_sources(
    snapshot_collector, mock_metrics_reader, mock_collection_tracker
):
    """Test that each snapshot field comes from the correct source."""
    mock_metrics_reader.get_current_memory_usage.return_value = 123.45
    mock_metrics_reader.get_system_memory_percent.return_value = 67.89
    mock_metrics_reader.get_current_task_count.return_value = 42
    mock_collection_tracker.get_collection_sizes.return_value = {"test": 999}

    result = snapshot_collector.take_snapshot()

    assert result.process_memory_mb == 123.45
    assert result.system_memory_percent == 67.89
    assert result.task_count == 42
    assert result.collection_sizes == {"test": 999}
