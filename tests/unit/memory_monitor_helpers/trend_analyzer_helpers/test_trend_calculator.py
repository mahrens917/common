"""Tests for TrendCalculator."""

import pytest

from common.memory_monitor_helpers.snapshot_collector import MemorySnapshot
from common.memory_monitor_helpers.trend_analyzer_helpers.trend_calculator import (
    TrendCalculator,
)


class TestTrendCalculatorCalculateTrends:
    """Tests for TrendCalculator.calculate_trends method."""

    def test_returns_empty_list_when_fewer_than_ten_snapshots(self):
        """Test that no trends are calculated with fewer than 10 snapshots."""
        snapshots = [
            MemorySnapshot(
                timestamp=float(i),
                process_memory_mb=100.0 + i * 10,
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(9)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert result == []

    def test_returns_empty_list_when_exactly_nine_snapshots(self):
        """Test boundary condition with exactly 9 snapshots."""
        snapshots = [
            MemorySnapshot(
                timestamp=float(i),
                process_memory_mb=100.0 + i * 10,
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(9)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert result == []

    def test_returns_empty_list_when_time_span_is_zero(self):
        """Test that no trends are calculated when all timestamps are identical."""
        snapshots = [
            MemorySnapshot(
                timestamp=100.0,
                process_memory_mb=100.0 + i * 10,
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert result == []

    def test_returns_empty_list_when_time_span_is_negative(self):
        """Test that no trends are calculated when timestamps decrease."""
        snapshots = [
            MemorySnapshot(
                timestamp=float(10 - i),
                process_memory_mb=100.0 + i * 10,
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert result == []

    def test_returns_empty_list_when_memory_rate_below_critical_threshold(self):
        """Test that no alert is generated when memory growth is below threshold."""
        # Create snapshots spanning 54 seconds (0.9 min) with 4.5 MB growth
        # Rate: 4.5 MB / 0.9 min = 5.0 MB/min but need < 5.0, so use 4.4
        # 4.4 / 0.9 = 4.89 MB/min (below 5.0 threshold)
        snapshots = [
            MemorySnapshot(
                timestamp=float(i * 6),
                process_memory_mb=100.0 + (i * 4.4 / 9),
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert result == []

    def test_returns_empty_list_when_memory_rate_exactly_at_threshold(self):
        """Test boundary condition when memory rate is exactly 5.0 MB/min."""
        # Create snapshots spanning 54 seconds (0.9 min) with 4.5 MB growth
        # Rate: 4.5 MB / 0.9 min = 5.0 MB/min (not greater than threshold)
        snapshots = [
            MemorySnapshot(
                timestamp=float(i * 6),
                process_memory_mb=100.0 + (i * 4.5 / 9),
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert result == []

    def test_returns_alert_when_memory_rate_exceeds_critical_threshold(self):
        """Test that alert is generated when memory growth exceeds threshold."""
        # Create snapshots spanning 54 seconds (0.9 min) with 6.0 MB growth
        # Rate: 6.0 MB / 0.9 min = 6.67 MB/min (above 5.0 threshold)
        snapshots = [
            MemorySnapshot(
                timestamp=float(i * 6),
                process_memory_mb=100.0 + (i * 6.0 / 9),
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert len(result) == 1
        alert = result[0]
        assert alert["type"] == "memory_leak_trend"
        assert alert["severity"] == "critical"
        assert "6.7MB/min" in alert["message"]
        assert "0.9 minutes" in alert["message"]
        assert alert["rate_mb_per_min"] == pytest.approx(6.67, rel=1e-2)
        assert alert["total_growth_mb"] == pytest.approx(6.0, rel=1e-2)

    def test_uses_only_last_ten_snapshots(self):
        """Test that only the last 10 snapshots are used for trend calculation."""
        # Create 15 snapshots, but only last 10 should be analyzed
        # First 5 snapshots have slow growth, last 10 have rapid growth
        snapshots = []

        # First 5 snapshots: slow growth
        for i in range(5):
            snapshots.append(
                MemorySnapshot(
                    timestamp=float(i * 6),
                    process_memory_mb=100.0 + i * 0.1,
                    system_memory_percent=50.0,
                    collection_sizes={},
                    task_count=5,
                )
            )

        # Last 10 snapshots: rapid growth (6 MB over 54 seconds = 0.9 min)
        # Rate: 6.0 / 0.9 = 6.67 MB/min
        for i in range(10):
            snapshots.append(
                MemorySnapshot(
                    timestamp=float(30 + i * 6),
                    process_memory_mb=100.5 + (i * 6.0 / 9),
                    system_memory_percent=50.0,
                    collection_sizes={},
                    task_count=5,
                )
            )

        result = TrendCalculator.calculate_trends(snapshots)

        assert len(result) == 1
        alert = result[0]
        assert alert["rate_mb_per_min"] == pytest.approx(6.67, rel=1e-2)

    def test_calculates_correct_rate_for_different_time_spans(self):
        """Test that rate calculation works correctly for various time spans."""
        # Create snapshots spanning 108 seconds (1.8 min) with 12.0 MB growth
        # Rate: 12.0 MB / 1.8 min = 6.67 MB/min
        snapshots = [
            MemorySnapshot(
                timestamp=float(i * 12),
                process_memory_mb=100.0 + (i * 12.0 / 9),
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert len(result) == 1
        alert = result[0]
        assert alert["rate_mb_per_min"] == pytest.approx(6.67, rel=1e-2)
        assert alert["total_growth_mb"] == pytest.approx(12.0, rel=1e-2)
        assert "1.8 minutes" in alert["message"]

    def test_handles_negative_memory_growth(self):
        """Test that decreasing memory usage doesn't trigger an alert."""
        # Create snapshots with decreasing memory
        snapshots = [
            MemorySnapshot(
                timestamp=float(i * 6),
                process_memory_mb=200.0 - (i * 2.0 / 9),
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert result == []

    def test_handles_zero_memory_growth(self):
        """Test that no memory change doesn't trigger an alert."""
        snapshots = [
            MemorySnapshot(
                timestamp=float(i * 6),
                process_memory_mb=100.0,
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert result == []

    def test_empty_snapshots_list(self):
        """Test that empty list returns empty result."""
        result = TrendCalculator.calculate_trends([])

        assert result == []

    def test_handles_very_large_memory_growth(self):
        """Test that very large memory growth is handled correctly."""
        # Create snapshots with 100 MB growth over 54 seconds (0.9 min)
        # Rate: 100 MB / 0.9 min = 111.11 MB/min
        snapshots = [
            MemorySnapshot(
                timestamp=float(i * 6),
                process_memory_mb=100.0 + (i * 100.0 / 9),
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert len(result) == 1
        alert = result[0]
        assert alert["rate_mb_per_min"] == pytest.approx(111.11, rel=1e-2)
        assert alert["total_growth_mb"] == pytest.approx(100.0, rel=1e-2)

    def test_handles_very_small_positive_growth_above_threshold(self):
        """Test that small growth just above threshold triggers alert."""
        # Create snapshots with 5.01 MB growth over 60 seconds
        # Rate: 5.01 MB / 1 min = 5.01 MB/min
        snapshots = [
            MemorySnapshot(
                timestamp=float(i * 6),
                process_memory_mb=100.0 + (i * 5.01 / 9),
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert len(result) == 1
        alert = result[0]
        assert alert["rate_mb_per_min"] > 5.0

    def test_ignores_collection_sizes_and_other_snapshot_fields(self):
        """Test that only timestamp and process_memory_mb are used."""
        snapshots = [
            MemorySnapshot(
                timestamp=float(i * 6),
                process_memory_mb=100.0 + (i * 6.0 / 9),
                system_memory_percent=float(50 + i * 10),
                collection_sizes={"dict": i * 1000, "list": i * 500},
                task_count=i * 100,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert len(result) == 1
        alert = result[0]
        assert alert["rate_mb_per_min"] == pytest.approx(6.67, rel=1e-2)

    def test_handles_fractional_timestamps(self):
        """Test that fractional timestamps are handled correctly."""
        snapshots = [
            MemorySnapshot(
                timestamp=100.5 + i * 6.7,
                process_memory_mb=100.0 + (i * 6.0 / 9),
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert len(result) == 1
        alert = result[0]
        # Time span: (100.5 + 9*6.7) - 100.5 = 60.3 seconds
        # Rate: 6.0 MB / (60.3/60) min ≈ 5.97 MB/min
        assert alert["rate_mb_per_min"] > 5.0

    def test_handles_exactly_ten_snapshots(self):
        """Test boundary condition with exactly 10 snapshots."""
        snapshots = [
            MemorySnapshot(
                timestamp=float(i * 6),
                process_memory_mb=100.0 + (i * 6.0 / 9),
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert len(result) == 1
        alert = result[0]
        assert alert["rate_mb_per_min"] == pytest.approx(6.67, rel=1e-2)

    def test_message_format_contains_all_required_information(self):
        """Test that alert message is formatted correctly."""
        snapshots = [
            MemorySnapshot(
                timestamp=float(i * 6),
                process_memory_mb=100.0 + (i * 6.0 / 9),
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert len(result) == 1
        alert = result[0]
        message = alert["message"]
        assert "Sustained memory growth:" in message
        assert "MB/min" in message
        assert "over" in message
        assert "minutes" in message

    def test_critical_rate_constant_is_accessible(self):
        """Test that CRITICAL_RATE_MB_PER_MIN constant is accessible."""
        assert TrendCalculator.CRITICAL_RATE_MB_PER_MIN == 5.0

    def test_alert_structure_contains_all_expected_keys(self):
        """Test that alert dictionary contains all expected keys."""
        snapshots = [
            MemorySnapshot(
                timestamp=float(i * 6),
                process_memory_mb=100.0 + (i * 6.0 / 9),
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert len(result) == 1
        alert = result[0]
        assert "type" in alert
        assert "severity" in alert
        assert "message" in alert
        assert "rate_mb_per_min" in alert
        assert "total_growth_mb" in alert
        assert len(alert) == 5

    def test_alert_values_have_correct_types(self):
        """Test that alert values have expected types."""
        snapshots = [
            MemorySnapshot(
                timestamp=float(i * 6),
                process_memory_mb=100.0 + (i * 6.0 / 9),
                system_memory_percent=50.0,
                collection_sizes={},
                task_count=5,
            )
            for i in range(10)
        ]

        result = TrendCalculator.calculate_trends(snapshots)

        assert len(result) == 1
        alert = result[0]
        assert isinstance(alert["type"], str)
        assert isinstance(alert["severity"], str)
        assert isinstance(alert["message"], str)
        assert isinstance(alert["rate_mb_per_min"], float)
        assert isinstance(alert["total_growth_mb"], float)
