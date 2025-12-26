"""Tests for alerting.throttle module."""

import pytest

from common.alerting.models import Alert, AlertSeverity
from common.alerting.throttle import AlertThrottle


class TestAlertThrottle:
    """Tests for AlertThrottle class."""

    def test_init(self) -> None:
        """Test throttle initialization."""
        throttle = AlertThrottle(window_seconds=60.0, max_alerts=5)

        assert throttle._window_seconds == 60.0
        assert throttle._max_alerts == 5
        assert throttle._recent == {}

    def test_first_alert_allowed(self) -> None:
        """Test first alert is allowed."""
        throttle = AlertThrottle(window_seconds=60.0, max_alerts=5)
        alert = Alert(
            message="Test",
            severity=AlertSeverity.INFO,
            timestamp=1000.0,
            alert_type="test",
        )

        result = throttle.record(alert)

        assert result is True

    def test_alerts_under_limit_allowed(self) -> None:
        """Test alerts under limit are allowed."""
        throttle = AlertThrottle(window_seconds=60.0, max_alerts=3)

        for i in range(3):
            alert = Alert(
                message=f"Test {i}",
                severity=AlertSeverity.INFO,
                timestamp=1000.0 + i,
                alert_type="test",
            )
            result = throttle.record(alert)
            assert result is True

    def test_alerts_at_limit_blocked(self) -> None:
        """Test alerts at limit are blocked."""
        throttle = AlertThrottle(window_seconds=60.0, max_alerts=3)

        for i in range(3):
            alert = Alert(
                message=f"Test {i}",
                severity=AlertSeverity.INFO,
                timestamp=1000.0 + i,
                alert_type="test",
            )
            throttle.record(alert)

        blocked_alert = Alert(
            message="Blocked",
            severity=AlertSeverity.INFO,
            timestamp=1005.0,
            alert_type="test",
        )
        result = throttle.record(blocked_alert)

        assert result is False

    def test_different_alert_types_tracked_separately(self) -> None:
        """Test different alert types have separate limits."""
        throttle = AlertThrottle(window_seconds=60.0, max_alerts=2)

        alert1 = Alert(
            message="Type A",
            severity=AlertSeverity.INFO,
            timestamp=1000.0,
            alert_type="type_a",
        )
        alert2 = Alert(
            message="Type A",
            severity=AlertSeverity.INFO,
            timestamp=1001.0,
            alert_type="type_a",
        )
        alert3 = Alert(
            message="Type B",
            severity=AlertSeverity.INFO,
            timestamp=1002.0,
            alert_type="type_b",
        )

        assert throttle.record(alert1) is True
        assert throttle.record(alert2) is True
        assert throttle.record(alert3) is True

    def test_old_alerts_pruned(self) -> None:
        """Test old alerts are pruned from window."""
        throttle = AlertThrottle(window_seconds=10.0, max_alerts=2)

        old_alert = Alert(
            message="Old",
            severity=AlertSeverity.INFO,
            timestamp=1000.0,
            alert_type="test",
        )
        throttle.record(old_alert)

        old_alert2 = Alert(
            message="Old2",
            severity=AlertSeverity.INFO,
            timestamp=1005.0,
            alert_type="test",
        )
        throttle.record(old_alert2)

        new_alert = Alert(
            message="New",
            severity=AlertSeverity.INFO,
            timestamp=1015.0,
            alert_type="test",
        )
        result = throttle.record(new_alert)

        assert result is True

    def test_window_boundary_blocked(self) -> None:
        """Test alert exactly at window boundary is blocked (strict less than)."""
        throttle = AlertThrottle(window_seconds=10.0, max_alerts=1)

        first_alert = Alert(
            message="First",
            severity=AlertSeverity.INFO,
            timestamp=1000.0,
            alert_type="test",
        )
        throttle.record(first_alert)

        boundary_alert = Alert(
            message="Boundary",
            severity=AlertSeverity.INFO,
            timestamp=1010.0,
            alert_type="test",
        )
        result = throttle.record(boundary_alert)

        assert result is False

    def test_just_past_window_allowed(self) -> None:
        """Test alert just past window boundary is allowed."""
        throttle = AlertThrottle(window_seconds=10.0, max_alerts=1)

        first_alert = Alert(
            message="First",
            severity=AlertSeverity.INFO,
            timestamp=1000.0,
            alert_type="test",
        )
        throttle.record(first_alert)

        past_boundary_alert = Alert(
            message="Past Boundary",
            severity=AlertSeverity.INFO,
            timestamp=1010.1,
            alert_type="test",
        )
        result = throttle.record(past_boundary_alert)

        assert result is True

    def test_prune_empties_queue(self) -> None:
        """Test prune removes all old entries."""
        throttle = AlertThrottle(window_seconds=5.0, max_alerts=10)

        for i in range(5):
            alert = Alert(
                message=f"Old {i}",
                severity=AlertSeverity.INFO,
                timestamp=1000.0 + i,
                alert_type="test",
            )
            throttle.record(alert)

        new_alert = Alert(
            message="New",
            severity=AlertSeverity.INFO,
            timestamp=1100.0,
            alert_type="test",
        )
        throttle.record(new_alert)

        assert len(throttle._recent["test"]) == 1
