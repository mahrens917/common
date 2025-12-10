"""Tests for alert builder."""

from typing import Dict

from common.memory_monitor_helpers.snapshot_collector import MemorySnapshot
from common.memory_monitor_helpers.trend_analyzer_helpers.alert_builder import (
    AlertBuilder,
)


def test_init_stores_task_count_threshold():
    """Test that initialization stores task count threshold."""
    builder = AlertBuilder(task_count_threshold=100)
    assert builder.task_count_threshold == 100


def test_init_accepts_zero_threshold():
    """Test that initialization accepts zero as threshold."""
    builder = AlertBuilder(task_count_threshold=0)
    assert builder.task_count_threshold == 0


def test_init_accepts_negative_threshold():
    """Test that initialization accepts negative threshold."""
    builder = AlertBuilder(task_count_threshold=-1)
    assert builder.task_count_threshold == -1


def test_build_task_count_alert_returns_empty_list_when_below_threshold():
    """Test that no alert is generated when task count is below threshold."""
    builder = AlertBuilder(task_count_threshold=100)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=150.0,
        system_memory_percent=50.0,
        collection_sizes={"list": 10, "dict": 20},
        task_count=99,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert alerts == []


def test_build_task_count_alert_returns_empty_list_when_equal_to_threshold():
    """Test that no alert is generated when task count equals threshold."""
    builder = AlertBuilder(task_count_threshold=100)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=150.0,
        system_memory_percent=50.0,
        collection_sizes={"list": 10, "dict": 20},
        task_count=100,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert alerts == []


def test_build_task_count_alert_returns_alert_when_exceeds_threshold():
    """Test that alert is generated when task count exceeds threshold."""
    builder = AlertBuilder(task_count_threshold=100)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=150.0,
        system_memory_percent=50.0,
        collection_sizes={"list": 10, "dict": 20},
        task_count=101,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert len(alerts) == 1
    assert alerts[0]["type"] == "high_task_count"
    assert alerts[0]["severity"] == "warning"
    assert alerts[0]["message"] == "High task count: 101 active tasks"
    assert alerts[0]["task_count"] == 101


def test_build_task_count_alert_structure_with_high_task_count():
    """Test that alert has correct structure when task count is high."""
    builder = AlertBuilder(task_count_threshold=50)
    snapshot = MemorySnapshot(
        timestamp=9999999999.0,
        process_memory_mb=500.0,
        system_memory_percent=80.0,
        collection_sizes={},
        task_count=200,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert isinstance(alerts, list)
    assert len(alerts) == 1
    alert = alerts[0]
    assert isinstance(alert, dict)
    assert set(alert.keys()) == {"type", "severity", "message", "task_count"}


def test_build_task_count_alert_with_zero_threshold_and_one_task():
    """Test alert generation when threshold is zero and task count is one."""
    builder = AlertBuilder(task_count_threshold=0)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=100.0,
        system_memory_percent=30.0,
        collection_sizes={},
        task_count=1,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert len(alerts) == 1
    assert alerts[0]["task_count"] == 1
    assert alerts[0]["message"] == "High task count: 1 active tasks"


def test_build_task_count_alert_with_zero_tasks():
    """Test that no alert is generated with zero tasks."""
    builder = AlertBuilder(task_count_threshold=10)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=100.0,
        system_memory_percent=30.0,
        collection_sizes={},
        task_count=0,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert alerts == []


def test_build_task_count_alert_with_very_high_task_count():
    """Test alert generation with very high task count."""
    builder = AlertBuilder(task_count_threshold=1000)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=2000.0,
        system_memory_percent=90.0,
        collection_sizes={"tasks": 10000},
        task_count=999999,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert len(alerts) == 1
    assert alerts[0]["task_count"] == 999999
    assert alerts[0]["message"] == "High task count: 999999 active tasks"


def test_build_task_count_alert_does_not_modify_snapshot():
    """Test that building alert does not modify the input snapshot."""
    builder = AlertBuilder(task_count_threshold=50)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=150.0,
        system_memory_percent=50.0,
        collection_sizes={"list": 10},
        task_count=100,
    )

    original_timestamp = snapshot.timestamp
    original_task_count = snapshot.task_count
    original_memory = snapshot.process_memory_mb

    builder.build_task_count_alert(snapshot)

    assert snapshot.timestamp == original_timestamp
    assert snapshot.task_count == original_task_count
    assert snapshot.process_memory_mb == original_memory


def test_build_task_count_alert_ignores_other_snapshot_fields():
    """Test that alert generation only considers task_count."""
    builder = AlertBuilder(task_count_threshold=50)

    # High memory but low task count
    snapshot1 = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=99999.0,
        system_memory_percent=99.9,
        collection_sizes={"huge": 999999},
        task_count=10,
    )

    alerts1 = builder.build_task_count_alert(snapshot1)
    assert alerts1 == []

    # Low memory but high task count
    snapshot2 = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=1.0,
        system_memory_percent=0.1,
        collection_sizes={},
        task_count=100,
    )

    alerts2 = builder.build_task_count_alert(snapshot2)
    assert len(alerts2) == 1
    assert alerts2[0]["task_count"] == 100


def test_build_task_count_alert_empty_collection_sizes():
    """Test alert generation when collection_sizes is empty."""
    builder = AlertBuilder(task_count_threshold=20)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=100.0,
        system_memory_percent=30.0,
        collection_sizes={},
        task_count=50,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert len(alerts) == 1
    assert alerts[0]["task_count"] == 50


def test_build_task_count_alert_multiple_calls_independent():
    """Test that multiple calls to build_task_count_alert are independent."""
    builder = AlertBuilder(task_count_threshold=100)

    snapshot1 = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=100.0,
        system_memory_percent=30.0,
        collection_sizes={},
        task_count=50,
    )

    snapshot2 = MemorySnapshot(
        timestamp=1234567891.0,
        process_memory_mb=200.0,
        system_memory_percent=40.0,
        collection_sizes={},
        task_count=150,
    )

    alerts1 = builder.build_task_count_alert(snapshot1)
    alerts2 = builder.build_task_count_alert(snapshot2)

    assert alerts1 == []
    assert len(alerts2) == 1
    assert alerts2[0]["task_count"] == 150


def test_build_task_count_alert_returns_new_list_each_time():
    """Test that each call returns a new list instance."""
    builder = AlertBuilder(task_count_threshold=10)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=100.0,
        system_memory_percent=30.0,
        collection_sizes={},
        task_count=20,
    )

    alerts1 = builder.build_task_count_alert(snapshot)
    alerts2 = builder.build_task_count_alert(snapshot)

    assert alerts1 is not alerts2
    assert alerts1 == alerts2


def test_build_task_count_alert_alert_fields_are_immutable_types():
    """Test that alert fields use immutable types where possible."""
    builder = AlertBuilder(task_count_threshold=10)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=100.0,
        system_memory_percent=30.0,
        collection_sizes={},
        task_count=50,
    )

    alerts = builder.build_task_count_alert(snapshot)
    alert = alerts[0]

    assert isinstance(alert["type"], str)
    assert isinstance(alert["severity"], str)
    assert isinstance(alert["message"], str)
    assert isinstance(alert["task_count"], int)


def test_build_task_count_alert_negative_task_count_below_threshold():
    """Test with negative task count below threshold (edge case)."""
    builder = AlertBuilder(task_count_threshold=10)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=100.0,
        system_memory_percent=30.0,
        collection_sizes={},
        task_count=-5,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert alerts == []


def test_build_task_count_alert_negative_task_count_above_negative_threshold():
    """Test with negative task count above negative threshold."""
    builder = AlertBuilder(task_count_threshold=-10)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=100.0,
        system_memory_percent=30.0,
        collection_sizes={},
        task_count=-5,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert len(alerts) == 1
    assert alerts[0]["task_count"] == -5
    assert alerts[0]["message"] == "High task count: -5 active tasks"


def test_build_task_count_alert_boundary_just_above_threshold():
    """Test task count exactly one above threshold."""
    builder = AlertBuilder(task_count_threshold=999)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=100.0,
        system_memory_percent=30.0,
        collection_sizes={},
        task_count=1000,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert len(alerts) == 1
    assert alerts[0]["task_count"] == 1000


def test_build_task_count_alert_boundary_just_below_threshold():
    """Test task count exactly one below threshold."""
    builder = AlertBuilder(task_count_threshold=1000)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=100.0,
        system_memory_percent=30.0,
        collection_sizes={},
        task_count=999,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert alerts == []


def test_build_task_count_alert_with_large_collection_sizes():
    """Test that large collection_sizes dict doesn't affect alert."""
    builder = AlertBuilder(task_count_threshold=50)
    large_collections: Dict[str, int] = {f"collection_{i}": i * 1000 for i in range(100)}

    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=5000.0,
        system_memory_percent=95.0,
        collection_sizes=large_collections,
        task_count=100,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert len(alerts) == 1
    assert alerts[0]["task_count"] == 100
    assert "collection" not in alerts[0]["message"].lower()


def test_build_task_count_alert_message_format():
    """Test that alert message has correct format."""
    builder = AlertBuilder(task_count_threshold=5)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=100.0,
        system_memory_percent=30.0,
        collection_sizes={},
        task_count=42,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert alerts[0]["message"] == "High task count: 42 active tasks"
    assert "42" in alerts[0]["message"]
    assert "active tasks" in alerts[0]["message"]


def test_build_task_count_alert_severity_is_warning():
    """Test that alert severity is always 'warning'."""
    builder = AlertBuilder(task_count_threshold=10)

    # Test with moderately high count
    snapshot1 = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=100.0,
        system_memory_percent=30.0,
        collection_sizes={},
        task_count=50,
    )

    # Test with extremely high count
    snapshot2 = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=100.0,
        system_memory_percent=30.0,
        collection_sizes={},
        task_count=999999,
    )

    alerts1 = builder.build_task_count_alert(snapshot1)
    alerts2 = builder.build_task_count_alert(snapshot2)

    assert alerts1[0]["severity"] == "warning"
    assert alerts2[0]["severity"] == "warning"


def test_build_task_count_alert_type_is_high_task_count():
    """Test that alert type is always 'high_task_count'."""
    builder = AlertBuilder(task_count_threshold=10)
    snapshot = MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=100.0,
        system_memory_percent=30.0,
        collection_sizes={},
        task_count=50,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert alerts[0]["type"] == "high_task_count"


def test_build_task_count_alert_float_timestamp_handled():
    """Test that float timestamp values are handled correctly."""
    builder = AlertBuilder(task_count_threshold=10)
    snapshot = MemorySnapshot(
        timestamp=1234567890.123456,
        process_memory_mb=100.5,
        system_memory_percent=30.75,
        collection_sizes={},
        task_count=50,
    )

    alerts = builder.build_task_count_alert(snapshot)

    assert len(alerts) == 1
    assert alerts[0]["task_count"] == 50
