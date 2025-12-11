"""Tests for MetricsTracker."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from common.base_connection_manager_helpers.metrics_tracker import (
    ConnectionMetrics,
    MetricsTracker,
)


class TestConnectionMetrics:
    """Tests for ConnectionMetrics dataclass."""

    def test_init_with_defaults(self) -> None:
        """Initializes with default values."""
        metrics = ConnectionMetrics()

        assert metrics.total_connections == 0
        assert metrics.successful_connections == 0
        assert metrics.failed_connections == 0
        assert metrics.consecutive_failures == 0
        assert metrics.last_connection_time is None
        assert metrics.last_failure_time is None
        assert metrics.current_backoff_delay == 0.0
        assert metrics.total_reconnection_attempts == 0

    def test_init_with_custom_values(self) -> None:
        """Initializes with custom values."""
        metrics = ConnectionMetrics(
            total_connections=10,
            successful_connections=8,
            failed_connections=2,
            consecutive_failures=1,
            last_connection_time=1234567890.0,
            last_failure_time=1234567891.0,
            current_backoff_delay=5.0,
            total_reconnection_attempts=3,
        )

        assert metrics.total_connections == 10
        assert metrics.successful_connections == 8
        assert metrics.failed_connections == 2
        assert metrics.consecutive_failures == 1
        assert metrics.last_connection_time == 1234567890.0
        assert metrics.last_failure_time == 1234567891.0
        assert metrics.current_backoff_delay == 5.0
        assert metrics.total_reconnection_attempts == 3


class TestMetricsTracker:
    """Tests for MetricsTracker class."""

    def test_init_creates_empty_metrics(self) -> None:
        """Initializes with empty metrics."""
        tracker = MetricsTracker()

        assert tracker.metrics.total_connections == 0
        assert tracker.metrics.successful_connections == 0
        assert tracker.metrics.failed_connections == 0

    def test_record_success_increments_counter(self) -> None:
        """Records successful connection."""
        tracker = MetricsTracker()

        with patch("time.time", return_value=1234567890.0):
            tracker.record_success()

        assert tracker.metrics.successful_connections == 1
        assert tracker.metrics.last_connection_time == 1234567890.0

    def test_record_success_resets_consecutive_failures(self) -> None:
        """Resets consecutive failures on success."""
        tracker = MetricsTracker()
        tracker.metrics.consecutive_failures = 5

        tracker.record_success()

        assert tracker.metrics.consecutive_failures == 0

    def test_record_success_multiple_times(self) -> None:
        """Records multiple successful connections."""
        tracker = MetricsTracker()

        tracker.record_success()
        tracker.record_success()
        tracker.record_success()

        assert tracker.metrics.successful_connections == 3

    def test_record_failure_increments_counter(self) -> None:
        """Records failed connection."""
        tracker = MetricsTracker()

        with patch("time.time", return_value=1234567890.0):
            tracker.record_failure()

        assert tracker.metrics.failed_connections == 1
        assert tracker.metrics.last_failure_time == 1234567890.0

    def test_record_failure_increments_consecutive_failures(self) -> None:
        """Increments consecutive failures."""
        tracker = MetricsTracker()

        tracker.record_failure()
        tracker.record_failure()
        tracker.record_failure()

        assert tracker.metrics.consecutive_failures == 3

    def test_increment_total_connections(self) -> None:
        """Increments total connections."""
        tracker = MetricsTracker()

        tracker.increment_total_connections()
        tracker.increment_total_connections()

        assert tracker.metrics.total_connections == 2

    def test_increment_reconnection_attempts(self) -> None:
        """Increments reconnection attempts."""
        tracker = MetricsTracker()

        tracker.increment_reconnection_attempts()
        tracker.increment_reconnection_attempts()
        tracker.increment_reconnection_attempts()

        assert tracker.metrics.total_reconnection_attempts == 3

    def test_set_backoff_delay(self) -> None:
        """Sets backoff delay."""
        tracker = MetricsTracker()

        tracker.set_backoff_delay(2.5)

        assert tracker.metrics.current_backoff_delay == 2.5

    def test_get_metrics_returns_metrics_object(self) -> None:
        """Returns metrics object."""
        tracker = MetricsTracker()
        tracker.metrics.total_connections = 10

        metrics = tracker.get_metrics()

        assert metrics.total_connections == 10
        assert isinstance(metrics, ConnectionMetrics)

    def test_combined_operations(self) -> None:
        """Tests combined operations."""
        tracker = MetricsTracker()

        tracker.increment_total_connections()
        tracker.record_success()
        tracker.increment_total_connections()
        tracker.record_failure()
        tracker.increment_total_connections()
        tracker.record_failure()
        tracker.set_backoff_delay(1.5)
        tracker.increment_reconnection_attempts()

        metrics = tracker.get_metrics()
        assert metrics.total_connections == 3
        assert metrics.successful_connections == 1
        assert metrics.failed_connections == 2
        assert metrics.consecutive_failures == 2
        assert metrics.current_backoff_delay == 1.5
        assert metrics.total_reconnection_attempts == 1
