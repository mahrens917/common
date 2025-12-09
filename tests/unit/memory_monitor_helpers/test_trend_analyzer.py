"""Comprehensive unit tests for TrendAnalyzer.

Tests cover:
- TrendAnalyzer initialization and parameter storage
- analyze_memory_trends method with various snapshot scenarios
- Insufficient data handling (< 2 snapshots)
- Integration with helper modules (GrowthAnalyzer, AlertBuilder, TrendCalculator)
- Alert collection and aggregation from all sources
- Status reporting and result structure
- Edge cases and boundary conditions
"""

from unittest.mock import Mock, patch

import pytest

from src.common.memory_monitor_helpers.snapshot_collector import MemorySnapshot
from src.common.memory_monitor_helpers.trend_analyzer import TrendAnalyzer


@pytest.fixture
def trend_analyzer():
    """Create TrendAnalyzer instance with test parameters."""
    return TrendAnalyzer(
        memory_growth_threshold_mb=10.0,
        collection_growth_threshold=100,
        task_count_threshold=50,
        check_interval_seconds=60,
    )


@pytest.fixture
def sample_snapshot():
    """Create a sample memory snapshot."""
    return MemorySnapshot(
        timestamp=1234567890.0,
        process_memory_mb=150.5,
        system_memory_percent=60.2,
        collection_sizes={"cache": 100, "queue": 20},
        task_count=10,
    )


@pytest.fixture
def previous_snapshot():
    """Create a previous memory snapshot."""
    return MemorySnapshot(
        timestamp=1234567830.0,
        process_memory_mb=140.0,
        system_memory_percent=58.0,
        collection_sizes={"cache": 80, "queue": 15},
        task_count=8,
    )


class TestTrendAnalyzerInit:
    """Tests for TrendAnalyzer initialization."""

    def test_init_stores_memory_growth_threshold(self):
        """Test that __init__ stores memory_growth_threshold_mb correctly."""
        analyzer = TrendAnalyzer(
            memory_growth_threshold_mb=15.5,
            collection_growth_threshold=200,
            task_count_threshold=75,
            check_interval_seconds=120,
        )
        assert analyzer.memory_growth_threshold_mb == 15.5

    def test_init_stores_collection_growth_threshold(self):
        """Test that __init__ stores collection_growth_threshold correctly."""
        analyzer = TrendAnalyzer(
            memory_growth_threshold_mb=10.0,
            collection_growth_threshold=250,
            task_count_threshold=50,
            check_interval_seconds=60,
        )
        assert analyzer.collection_growth_threshold == 250

    def test_init_stores_task_count_threshold(self):
        """Test that __init__ stores task_count_threshold correctly."""
        analyzer = TrendAnalyzer(
            memory_growth_threshold_mb=10.0,
            collection_growth_threshold=100,
            task_count_threshold=100,
            check_interval_seconds=60,
        )
        assert analyzer.task_count_threshold == 100

    def test_init_stores_check_interval_seconds(self):
        """Test that __init__ stores check_interval_seconds correctly."""
        analyzer = TrendAnalyzer(
            memory_growth_threshold_mb=10.0,
            collection_growth_threshold=100,
            task_count_threshold=50,
            check_interval_seconds=180,
        )
        assert analyzer.check_interval_seconds == 180

    def test_init_accepts_zero_thresholds(self):
        """Test that __init__ accepts zero thresholds."""
        analyzer = TrendAnalyzer(
            memory_growth_threshold_mb=0.0,
            collection_growth_threshold=0,
            task_count_threshold=0,
            check_interval_seconds=1,
        )
        assert analyzer.memory_growth_threshold_mb == 0.0
        assert analyzer.collection_growth_threshold == 0
        assert analyzer.task_count_threshold == 0

    def test_init_accepts_negative_thresholds(self):
        """Test that __init__ accepts negative values (no validation)."""
        analyzer = TrendAnalyzer(
            memory_growth_threshold_mb=-5.0,
            collection_growth_threshold=-10,
            task_count_threshold=-20,
            check_interval_seconds=-30,
        )
        assert analyzer.memory_growth_threshold_mb == -5.0
        assert analyzer.collection_growth_threshold == -10
        assert analyzer.task_count_threshold == -20
        assert analyzer.check_interval_seconds == -30


class TestAnalyzeMemoryTrendsInsufficientData:
    """Tests for analyze_memory_trends with insufficient data."""

    def test_analyze_memory_trends_returns_insufficient_data_with_empty_list(self, trend_analyzer):
        """Test that analyze_memory_trends returns insufficient_data status with empty list."""
        result = trend_analyzer.analyze_memory_trends([])
        assert result == {"status": "insufficient_data", "alerts": []}

    def test_analyze_memory_trends_returns_insufficient_data_with_one_snapshot(
        self, trend_analyzer, sample_snapshot
    ):
        """Test that analyze_memory_trends returns insufficient_data status with one snapshot."""
        result = trend_analyzer.analyze_memory_trends([sample_snapshot])
        assert result == {"status": "insufficient_data", "alerts": []}

    def test_analyze_memory_trends_does_not_call_helpers_with_insufficient_data(
        self, trend_analyzer, sample_snapshot
    ):
        """Test that helpers are not called when there's insufficient data."""
        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend,
        ):
            trend_analyzer.analyze_memory_trends([sample_snapshot])

            mock_growth.assert_not_called()
            mock_alert.assert_not_called()
            mock_trend.calculate_trends.assert_not_called()


class TestAnalyzeMemoryTrendsWithSufficientData:
    """Tests for analyze_memory_trends with sufficient data."""

    def test_analyze_memory_trends_creates_growth_analyzer_with_correct_params(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that GrowthAnalyzer is created with correct parameters."""
        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch("src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"),
            patch("src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"),
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            trend_analyzer.analyze_memory_trends([previous_snapshot, sample_snapshot])

            mock_growth_class.assert_called_once_with(
                trend_analyzer.memory_growth_threshold_mb,
                trend_analyzer.collection_growth_threshold,
                trend_analyzer.check_interval_seconds,
            )

    def test_analyze_memory_trends_creates_alert_builder_with_correct_params(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that AlertBuilder is created with correct parameters."""
        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch("src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"),
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            trend_analyzer.analyze_memory_trends([previous_snapshot, sample_snapshot])

            mock_alert_class.assert_called_once_with(trend_analyzer.task_count_threshold)

    def test_analyze_memory_trends_calls_analyze_memory_growth(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that analyze_memory_growth is called with current and previous snapshots."""
        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch("src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"),
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            trend_analyzer.analyze_memory_trends([previous_snapshot, sample_snapshot])

            mock_growth_instance.analyze_memory_growth.assert_called_once_with(
                sample_snapshot, previous_snapshot
            )

    def test_analyze_memory_trends_calls_analyze_collection_growth(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that analyze_collection_growth is called with current and previous snapshots."""
        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch("src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"),
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            trend_analyzer.analyze_memory_trends([previous_snapshot, sample_snapshot])

            mock_growth_instance.analyze_collection_growth.assert_called_once_with(
                sample_snapshot, previous_snapshot
            )

    def test_analyze_memory_trends_calls_build_task_count_alert(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that build_task_count_alert is called with current snapshot."""
        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch("src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"),
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            trend_analyzer.analyze_memory_trends([previous_snapshot, sample_snapshot])

            mock_alert_instance.build_task_count_alert.assert_called_once_with(sample_snapshot)

    def test_analyze_memory_trends_calls_calculate_trends(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that TrendCalculator.calculate_trends is called with all snapshots."""
        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = []

            snapshots = [previous_snapshot, sample_snapshot]
            trend_analyzer.analyze_memory_trends(snapshots)

            mock_trend_class.calculate_trends.assert_called_once_with(snapshots)

    def test_analyze_memory_trends_uses_last_two_snapshots(self, trend_analyzer):
        """Test that analyze_memory_trends uses the last two snapshots correctly."""
        snapshot1 = MemorySnapshot(
            timestamp=100.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )
        snapshot2 = MemorySnapshot(
            timestamp=200.0,
            process_memory_mb=110.0,
            system_memory_percent=55.0,
            collection_sizes={},
            task_count=6,
        )
        snapshot3 = MemorySnapshot(
            timestamp=300.0,
            process_memory_mb=120.0,
            system_memory_percent=60.0,
            collection_sizes={},
            task_count=7,
        )

        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch("src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"),
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            trend_analyzer.analyze_memory_trends([snapshot1, snapshot2, snapshot3])

            # Should use snapshot3 (current) and snapshot2 (previous)
            mock_growth_instance.analyze_memory_growth.assert_called_once_with(snapshot3, snapshot2)
            mock_growth_instance.analyze_collection_growth.assert_called_once_with(
                snapshot3, snapshot2
            )
            mock_alert_instance.build_task_count_alert.assert_called_once_with(snapshot3)


class TestAnalyzeMemoryTrendsAlertAggregation:
    """Tests for alert aggregation in analyze_memory_trends."""

    def test_analyze_memory_trends_aggregates_all_alerts(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that all alerts from different sources are aggregated."""
        memory_alert = {"type": "memory_growth", "severity": "warning"}
        collection_alert = {"type": "collection_growth", "severity": "error"}
        task_alert = {"type": "high_task_count", "severity": "warning"}
        trend_alert = {"type": "memory_leak_trend", "severity": "critical"}

        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = [memory_alert]
            mock_growth_instance.analyze_collection_growth.return_value = [collection_alert]
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = [task_alert]
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = [trend_alert]

            result = trend_analyzer.analyze_memory_trends([previous_snapshot, sample_snapshot])

            assert result["alerts"] == [memory_alert, collection_alert, task_alert, trend_alert]

    def test_analyze_memory_trends_handles_empty_alerts_from_all_sources(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that empty alert lists are handled correctly."""
        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = []

            result = trend_analyzer.analyze_memory_trends([previous_snapshot, sample_snapshot])

            assert result["alerts"] == []

    def test_analyze_memory_trends_handles_multiple_alerts_from_single_source(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that multiple alerts from a single source are all included."""
        collection_alert1 = {"type": "collection_growth", "collection": "cache"}
        collection_alert2 = {"type": "collection_growth", "collection": "queue"}

        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = [
                collection_alert1,
                collection_alert2,
            ]
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = []

            result = trend_analyzer.analyze_memory_trends([previous_snapshot, sample_snapshot])

            assert result["alerts"] == [collection_alert1, collection_alert2]


class TestAnalyzeMemoryTrendsResultStructure:
    """Tests for the result structure of analyze_memory_trends."""

    def test_analyze_memory_trends_returns_analyzed_status(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that status is 'analyzed' when sufficient data is available."""
        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = []

            result = trend_analyzer.analyze_memory_trends([previous_snapshot, sample_snapshot])

            assert result["status"] == "analyzed"

    def test_analyze_memory_trends_includes_current_memory_mb(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that result includes current_memory_mb from current snapshot."""
        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = []

            result = trend_analyzer.analyze_memory_trends([previous_snapshot, sample_snapshot])

            assert result["current_memory_mb"] == sample_snapshot.process_memory_mb

    def test_analyze_memory_trends_includes_system_memory_percent(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that result includes system_memory_percent from current snapshot."""
        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = []

            result = trend_analyzer.analyze_memory_trends([previous_snapshot, sample_snapshot])

            assert result["system_memory_percent"] == sample_snapshot.system_memory_percent

    def test_analyze_memory_trends_includes_task_count(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that result includes task_count from current snapshot."""
        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = []

            result = trend_analyzer.analyze_memory_trends([previous_snapshot, sample_snapshot])

            assert result["task_count"] == sample_snapshot.task_count

    def test_analyze_memory_trends_includes_collection_sizes(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that result includes collection_sizes from current snapshot."""
        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = []

            result = trend_analyzer.analyze_memory_trends([previous_snapshot, sample_snapshot])

            assert result["collection_sizes"] == sample_snapshot.collection_sizes

    def test_analyze_memory_trends_includes_all_required_fields(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that result includes all required fields."""
        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = []

            result = trend_analyzer.analyze_memory_trends([previous_snapshot, sample_snapshot])

            expected_keys = {
                "status",
                "current_memory_mb",
                "system_memory_percent",
                "task_count",
                "collection_sizes",
                "alerts",
            }
            assert set(result.keys()) == expected_keys


class TestAnalyzeMemoryTrendsEdgeCases:
    """Tests for edge cases in analyze_memory_trends."""

    def test_analyze_memory_trends_with_exactly_two_snapshots(
        self, trend_analyzer, sample_snapshot, previous_snapshot
    ):
        """Test that analyze_memory_trends works correctly with exactly 2 snapshots."""
        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = []

            result = trend_analyzer.analyze_memory_trends([previous_snapshot, sample_snapshot])

            assert result["status"] == "analyzed"
            assert "alerts" in result

    def test_analyze_memory_trends_with_empty_collection_sizes(self, trend_analyzer):
        """Test that analyze_memory_trends handles empty collection_sizes."""
        snapshot1 = MemorySnapshot(
            timestamp=100.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )
        snapshot2 = MemorySnapshot(
            timestamp=200.0,
            process_memory_mb=110.0,
            system_memory_percent=55.0,
            collection_sizes={},
            task_count=6,
        )

        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = []

            result = trend_analyzer.analyze_memory_trends([snapshot1, snapshot2])

            assert result["collection_sizes"] == {}
            assert result["status"] == "analyzed"

    def test_analyze_memory_trends_with_zero_task_count(self, trend_analyzer):
        """Test that analyze_memory_trends handles zero task_count."""
        snapshot1 = MemorySnapshot(
            timestamp=100.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 10},
            task_count=0,
        )
        snapshot2 = MemorySnapshot(
            timestamp=200.0,
            process_memory_mb=110.0,
            system_memory_percent=55.0,
            collection_sizes={"cache": 15},
            task_count=0,
        )

        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = []

            result = trend_analyzer.analyze_memory_trends([snapshot1, snapshot2])

            assert result["task_count"] == 0
            assert result["status"] == "analyzed"

    def test_analyze_memory_trends_with_zero_memory_usage(self, trend_analyzer):
        """Test that analyze_memory_trends handles zero memory usage."""
        snapshot1 = MemorySnapshot(
            timestamp=100.0,
            process_memory_mb=0.0,
            system_memory_percent=0.0,
            collection_sizes={},
            task_count=0,
        )
        snapshot2 = MemorySnapshot(
            timestamp=200.0,
            process_memory_mb=0.0,
            system_memory_percent=0.0,
            collection_sizes={},
            task_count=0,
        )

        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = []

            result = trend_analyzer.analyze_memory_trends([snapshot1, snapshot2])

            assert result["current_memory_mb"] == 0.0
            assert result["system_memory_percent"] == 0.0
            assert result["status"] == "analyzed"

    def test_analyze_memory_trends_with_many_snapshots(self, trend_analyzer):
        """Test that analyze_memory_trends passes all snapshots to TrendCalculator."""
        snapshots = [
            MemorySnapshot(
                timestamp=float(i * 100),
                process_memory_mb=100.0 + i * 10,
                system_memory_percent=50.0 + i,
                collection_sizes={"cache": i * 5},
                task_count=i,
            )
            for i in range(20)
        ]

        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = []

            result = trend_analyzer.analyze_memory_trends(snapshots)

            # Should use last two snapshots for growth analysis
            mock_growth_instance.analyze_memory_growth.assert_called_once_with(
                snapshots[-1], snapshots[-2]
            )
            # But pass all snapshots to TrendCalculator
            mock_trend_class.calculate_trends.assert_called_once_with(snapshots)
            assert result["status"] == "analyzed"

    def test_analyze_memory_trends_with_negative_memory_values(self, trend_analyzer):
        """Test that analyze_memory_trends handles negative memory values (edge case)."""
        snapshot1 = MemorySnapshot(
            timestamp=100.0,
            process_memory_mb=-10.0,
            system_memory_percent=-5.0,
            collection_sizes={},
            task_count=0,
        )
        snapshot2 = MemorySnapshot(
            timestamp=200.0,
            process_memory_mb=-5.0,
            system_memory_percent=-2.0,
            collection_sizes={},
            task_count=0,
        )

        with (
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.GrowthAnalyzer"
            ) as mock_growth_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.AlertBuilder"
            ) as mock_alert_class,
            patch(
                "src.common.memory_monitor_helpers.trend_analyzer_helpers.TrendCalculator"
            ) as mock_trend_class,
        ):
            mock_growth_instance = Mock()
            mock_growth_instance.analyze_memory_growth.return_value = []
            mock_growth_instance.analyze_collection_growth.return_value = []
            mock_growth_class.return_value = mock_growth_instance

            mock_alert_instance = Mock()
            mock_alert_instance.build_task_count_alert.return_value = []
            mock_alert_class.return_value = mock_alert_instance

            mock_trend_class.calculate_trends.return_value = []

            result = trend_analyzer.analyze_memory_trends([snapshot1, snapshot2])

            assert result["current_memory_mb"] == -5.0
            assert result["system_memory_percent"] == -2.0
            assert result["status"] == "analyzed"
