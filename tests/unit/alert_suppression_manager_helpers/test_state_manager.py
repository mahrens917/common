"""Tests for alert suppression state manager."""

import pytest

from src.common.alert_suppression_manager_helpers.state_manager import StateManager
from src.common.alert_suppression_manager_helpers.suppression_tracker import (
    AlertType,
    SuppressionDecision,
    SuppressionTracker,
)


@pytest.fixture
def tracker():
    """Create a suppression tracker for tests."""
    return SuppressionTracker()


@pytest.fixture
def state_manager(tracker):
    """Create a state manager for tests."""
    return StateManager(tracker)


def test_state_manager_initialization(tracker):
    """Test state manager initialization."""
    manager = StateManager(tracker)
    assert manager.tracker == tracker


def test_get_suppression_statistics_empty(state_manager):
    """Test getting statistics when no decisions recorded."""
    stats = state_manager.get_suppression_statistics(
        enabled=True,
        grace_period_seconds=300,
        max_suppression_duration_seconds=1800,
        suppressed_alert_types=[AlertType.ERROR_LOG],
    )

    assert stats["total_decisions"] == 0
    assert stats["suppressed_count"] == 0
    assert stats["suppression_rate"] == 0.0
    assert stats["by_service"] == {}
    assert stats["by_alert_type"] == {}


def test_get_suppression_statistics_with_decisions(state_manager):
    """Test getting statistics with recorded decisions."""
    decisions = [
        SuppressionDecision(True, "Test 1", "kalshi", AlertType.ERROR_LOG),
        SuppressionDecision(False, "Test 2", "kalshi", AlertType.ERROR_LOG),
        SuppressionDecision(True, "Test 3", "weather", AlertType.STALE_LOG),
    ]

    for decision in decisions:
        state_manager.tracker.record_decision(decision)

    stats = state_manager.get_suppression_statistics(
        enabled=True,
        grace_period_seconds=300,
        max_suppression_duration_seconds=1800,
        suppressed_alert_types=[AlertType.ERROR_LOG, AlertType.STALE_LOG],
    )

    assert stats["total_decisions"] == 3
    assert stats["suppressed_count"] == 2
    assert stats["suppression_rate"] == 2 / 3


def test_get_suppression_statistics_by_service(state_manager):
    """Test by_service statistics."""
    state_manager.tracker.record_decision(
        SuppressionDecision(True, "Test", "kalshi", AlertType.ERROR_LOG)
    )
    state_manager.tracker.record_decision(
        SuppressionDecision(False, "Test", "kalshi", AlertType.ERROR_LOG)
    )
    state_manager.tracker.record_decision(
        SuppressionDecision(True, "Test", "weather", AlertType.STALE_LOG)
    )

    stats = state_manager.get_suppression_statistics(
        enabled=True,
        grace_period_seconds=300,
        max_suppression_duration_seconds=1800,
        suppressed_alert_types=[],
    )

    assert "kalshi" in stats["by_service"]
    assert stats["by_service"]["kalshi"]["total"] == 2
    assert stats["by_service"]["kalshi"]["suppressed"] == 1

    assert "weather" in stats["by_service"]
    assert stats["by_service"]["weather"]["total"] == 1
    assert stats["by_service"]["weather"]["suppressed"] == 1


def test_get_suppression_statistics_by_alert_type(state_manager):
    """Test by_alert_type statistics."""
    state_manager.tracker.record_decision(
        SuppressionDecision(True, "Test", "kalshi", AlertType.ERROR_LOG)
    )
    state_manager.tracker.record_decision(
        SuppressionDecision(False, "Test", "kalshi", AlertType.ERROR_LOG)
    )
    state_manager.tracker.record_decision(
        SuppressionDecision(True, "Test", "weather", AlertType.STALE_LOG)
    )

    stats = state_manager.get_suppression_statistics(
        enabled=True,
        grace_period_seconds=300,
        max_suppression_duration_seconds=1800,
        suppressed_alert_types=[],
    )

    assert "error_log" in stats["by_alert_type"]
    assert stats["by_alert_type"]["error_log"]["total"] == 2
    assert stats["by_alert_type"]["error_log"]["suppressed"] == 1

    assert "stale_log" in stats["by_alert_type"]
    assert stats["by_alert_type"]["stale_log"]["total"] == 1
    assert stats["by_alert_type"]["stale_log"]["suppressed"] == 1


def test_get_suppression_statistics_includes_rule_config(state_manager):
    """Test that statistics include rule configuration."""
    stats = state_manager.get_suppression_statistics(
        enabled=True,
        grace_period_seconds=600,
        max_suppression_duration_seconds=3600,
        suppressed_alert_types=[AlertType.ERROR_LOG, AlertType.RECOVERY],
    )

    assert "rule_config" in stats
    assert stats["rule_config"]["enabled"] is True
    assert stats["rule_config"]["grace_period_seconds"] == 600
    assert stats["rule_config"]["max_suppression_duration_seconds"] == 3600
    assert stats["rule_config"]["suppressed_alert_types"] == [
        AlertType.ERROR_LOG,
        AlertType.RECOVERY,
    ]


def test_get_suppression_statistics_all_suppressed(state_manager):
    """Test statistics when all decisions are suppressed."""
    for i in range(5):
        state_manager.tracker.record_decision(
            SuppressionDecision(True, f"Test {i}", "service", AlertType.ERROR_LOG)
        )

    stats = state_manager.get_suppression_statistics(
        enabled=True,
        grace_period_seconds=300,
        max_suppression_duration_seconds=1800,
        suppressed_alert_types=[],
    )

    assert stats["total_decisions"] == 5
    assert stats["suppressed_count"] == 5
    assert stats["suppression_rate"] == 1.0


def test_get_suppression_statistics_none_suppressed(state_manager):
    """Test statistics when no decisions are suppressed."""
    for i in range(5):
        state_manager.tracker.record_decision(
            SuppressionDecision(False, f"Test {i}", "service", AlertType.ERROR_LOG)
        )

    stats = state_manager.get_suppression_statistics(
        enabled=True,
        grace_period_seconds=300,
        max_suppression_duration_seconds=1800,
        suppressed_alert_types=[],
    )

    assert stats["total_decisions"] == 5
    assert stats["suppressed_count"] == 0
    assert stats["suppression_rate"] == 0.0


def test_compute_by_service_stats_multiple_services(state_manager):
    """Test by_service computation with multiple services."""
    decisions = [
        SuppressionDecision(True, "Test", "kalshi", AlertType.ERROR_LOG),
        SuppressionDecision(True, "Test", "kalshi", AlertType.ERROR_LOG),
        SuppressionDecision(False, "Test", "weather", AlertType.ERROR_LOG),
        SuppressionDecision(True, "Test", "deribit", AlertType.ERROR_LOG),
    ]

    by_service = state_manager._compute_by_service_stats(decisions)

    assert len(by_service) == 3
    assert by_service["kalshi"]["total"] == 2
    assert by_service["kalshi"]["suppressed"] == 2
    assert by_service["weather"]["total"] == 1
    assert by_service["weather"]["suppressed"] == 0
    assert by_service["deribit"]["total"] == 1
    assert by_service["deribit"]["suppressed"] == 1


def test_compute_by_alert_type_stats_multiple_types(state_manager):
    """Test by_alert_type computation with multiple alert types."""
    decisions = [
        SuppressionDecision(True, "Test", "service", AlertType.ERROR_LOG),
        SuppressionDecision(True, "Test", "service", AlertType.ERROR_LOG),
        SuppressionDecision(False, "Test", "service", AlertType.STALE_LOG),
        SuppressionDecision(True, "Test", "service", AlertType.RECOVERY),
    ]

    by_alert_type = state_manager._compute_by_alert_type_stats(decisions)

    assert len(by_alert_type) == 3
    assert by_alert_type["error_log"]["total"] == 2
    assert by_alert_type["error_log"]["suppressed"] == 2
    assert by_alert_type["stale_log"]["total"] == 1
    assert by_alert_type["stale_log"]["suppressed"] == 0
    assert by_alert_type["recovery"]["total"] == 1
    assert by_alert_type["recovery"]["suppressed"] == 1
