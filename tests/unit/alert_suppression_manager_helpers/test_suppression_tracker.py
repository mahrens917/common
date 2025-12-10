"""Tests for alert suppression tracker."""

import pytest

from common.alert_suppression_manager_helpers.suppression_tracker import (
    AlertType,
    SuppressionDecision,
    SuppressionTracker,
)


def test_alert_type_enum_values():
    """Test that AlertType enum has expected values."""
    assert AlertType.ERROR_LOG.value == "error_log"
    assert AlertType.STALE_LOG.value == "stale_log"
    assert AlertType.MESSAGE_METRICS.value == "message_metrics"
    assert AlertType.HEALTH_CHECK.value == "health_check"
    assert AlertType.PROCESS_STATUS.value == "process_status"
    assert AlertType.RECOVERY.value == "recovery"
    assert AlertType.SYSTEM_RESOURCES.value == "system_resources"


def test_suppression_decision_creation():
    """Test creating a SuppressionDecision."""
    decision = SuppressionDecision(
        should_suppress=True,
        reason="During reconnection grace period",
        service_name="kalshi",
        alert_type=AlertType.ERROR_LOG,
        suppression_duration_seconds=30.0,
        grace_period_remaining_seconds=15.0,
    )

    assert decision.should_suppress is True
    assert decision.reason == "During reconnection grace period"
    assert decision.service_name == "kalshi"
    assert decision.alert_type == AlertType.ERROR_LOG
    assert decision.suppression_duration_seconds == 30.0
    assert decision.grace_period_remaining_seconds == 15.0


def test_suppression_decision_optional_fields():
    """Test SuppressionDecision with optional fields as None."""
    decision = SuppressionDecision(
        should_suppress=False,
        reason="Not in grace period",
        service_name="weather",
        alert_type=AlertType.HEALTH_CHECK,
    )

    assert decision.suppression_duration_seconds is None
    assert decision.grace_period_remaining_seconds is None


def test_tracker_initialization():
    """Test tracker initialization."""
    tracker = SuppressionTracker(max_history_entries=500)

    assert len(tracker.suppression_history) == 0
    assert tracker.max_history_entries == 500
    assert not tracker.has_history()


def test_tracker_default_max_entries():
    """Test tracker uses default max entries."""
    tracker = SuppressionTracker()

    assert tracker.max_history_entries == 1000


def test_record_decision():
    """Test recording a decision."""
    tracker = SuppressionTracker()

    decision = SuppressionDecision(
        should_suppress=True,
        reason="Test",
        service_name="test_service",
        alert_type=AlertType.ERROR_LOG,
    )

    tracker.record_decision(decision)

    assert len(tracker.suppression_history) == 1
    assert tracker.has_history()
    assert tracker.suppression_history[0] == decision


def test_record_multiple_decisions():
    """Test recording multiple decisions."""
    tracker = SuppressionTracker()

    for i in range(5):
        decision = SuppressionDecision(
            should_suppress=True,
            reason=f"Test {i}",
            service_name="test_service",
            alert_type=AlertType.ERROR_LOG,
        )
        tracker.record_decision(decision)

    assert len(tracker.suppression_history) == 5
    assert tracker.has_history()


def test_record_decision_trims_history():
    """Test that history is trimmed to max entries."""
    tracker = SuppressionTracker(max_history_entries=3)

    for i in range(5):
        decision = SuppressionDecision(
            should_suppress=True,
            reason=f"Test {i}",
            service_name="test_service",
            alert_type=AlertType.ERROR_LOG,
        )
        tracker.record_decision(decision)

    assert len(tracker.suppression_history) == 3
    # Should keep the most recent 3
    assert tracker.suppression_history[0].reason == "Test 2"
    assert tracker.suppression_history[1].reason == "Test 3"
    assert tracker.suppression_history[2].reason == "Test 4"


def test_get_recent_decisions_empty():
    """Test getting recent decisions when history is empty."""
    tracker = SuppressionTracker()

    recent = tracker.get_recent_decisions()

    assert recent == []


def test_get_recent_decisions_default_limit():
    """Test getting recent decisions with default limit."""
    tracker = SuppressionTracker()

    for i in range(100):
        decision = SuppressionDecision(
            should_suppress=True,
            reason=f"Test {i}",
            service_name="test_service",
            alert_type=AlertType.ERROR_LOG,
        )
        tracker.record_decision(decision)

    recent = tracker.get_recent_decisions()

    assert len(recent) == 50
    # Should get last 50
    assert recent[0].reason == "Test 50"
    assert recent[-1].reason == "Test 99"


def test_get_recent_decisions_custom_limit():
    """Test getting recent decisions with custom limit."""
    tracker = SuppressionTracker()

    for i in range(20):
        decision = SuppressionDecision(
            should_suppress=True,
            reason=f"Test {i}",
            service_name="test_service",
            alert_type=AlertType.ERROR_LOG,
        )
        tracker.record_decision(decision)

    recent = tracker.get_recent_decisions(limit=10)

    assert len(recent) == 10
    assert recent[0].reason == "Test 10"
    assert recent[-1].reason == "Test 19"


def test_get_recent_decisions_limit_exceeds_history():
    """Test getting recent decisions when limit exceeds history size."""
    tracker = SuppressionTracker()

    for i in range(5):
        decision = SuppressionDecision(
            should_suppress=True,
            reason=f"Test {i}",
            service_name="test_service",
            alert_type=AlertType.ERROR_LOG,
        )
        tracker.record_decision(decision)

    recent = tracker.get_recent_decisions(limit=50)

    assert len(recent) == 5


def test_has_history_true():
    """Test has_history returns True when decisions exist."""
    tracker = SuppressionTracker()

    decision = SuppressionDecision(
        should_suppress=True,
        reason="Test",
        service_name="test_service",
        alert_type=AlertType.ERROR_LOG,
    )
    tracker.record_decision(decision)

    assert tracker.has_history() is True


def test_has_history_false():
    """Test has_history returns False when no decisions."""
    tracker = SuppressionTracker()

    assert tracker.has_history() is False


def test_get_all_decisions():
    """Test getting all decisions."""
    tracker = SuppressionTracker()

    decisions = []
    for i in range(10):
        decision = SuppressionDecision(
            should_suppress=True,
            reason=f"Test {i}",
            service_name="test_service",
            alert_type=AlertType.ERROR_LOG,
        )
        tracker.record_decision(decision)
        decisions.append(decision)

    all_decisions = tracker.get_all_decisions()

    assert len(all_decisions) == 10
    assert all_decisions == decisions


def test_get_all_decisions_returns_copy():
    """Test that get_all_decisions returns a copy."""
    tracker = SuppressionTracker()

    decision = SuppressionDecision(
        should_suppress=True,
        reason="Test",
        service_name="test_service",
        alert_type=AlertType.ERROR_LOG,
    )
    tracker.record_decision(decision)

    all_decisions = tracker.get_all_decisions()
    all_decisions.clear()

    # Original should be unchanged
    assert len(tracker.suppression_history) == 1


def test_tracker_different_alert_types():
    """Test tracking decisions with different alert types."""
    tracker = SuppressionTracker()

    alert_types = [
        AlertType.ERROR_LOG,
        AlertType.STALE_LOG,
        AlertType.MESSAGE_METRICS,
        AlertType.HEALTH_CHECK,
        AlertType.PROCESS_STATUS,
        AlertType.RECOVERY,
        AlertType.SYSTEM_RESOURCES,
    ]

    for alert_type in alert_types:
        decision = SuppressionDecision(
            should_suppress=True,
            reason="Test",
            service_name="test_service",
            alert_type=alert_type,
        )
        tracker.record_decision(decision)

    assert len(tracker.suppression_history) == 7

    # Verify all alert types are present
    recorded_types = {d.alert_type for d in tracker.suppression_history}
    assert recorded_types == set(alert_types)
