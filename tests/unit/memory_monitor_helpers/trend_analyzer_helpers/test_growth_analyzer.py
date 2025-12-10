"""Tests for growth analyzer."""

import pytest

from common.memory_monitor_helpers.snapshot_collector import MemorySnapshot
from common.memory_monitor_helpers.trend_analyzer_helpers.growth_analyzer import (
    GrowthAnalyzer,
)


class TestGrowthAnalyzerInit:
    """Test GrowthAnalyzer initialization."""

    def test_initializes_with_valid_parameters(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        assert analyzer.memory_growth_threshold_mb == 50.0
        assert analyzer.collection_growth_threshold == 100
        assert analyzer.check_interval_seconds == 60

    def test_initializes_with_zero_thresholds(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=0.0,
            collection_growth_threshold=0,
            check_interval_seconds=1,
        )

        assert analyzer.memory_growth_threshold_mb == 0.0
        assert analyzer.collection_growth_threshold == 0
        assert analyzer.check_interval_seconds == 1

    def test_initializes_with_negative_thresholds(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=-10.0,
            collection_growth_threshold=-5,
            check_interval_seconds=30,
        )

        assert analyzer.memory_growth_threshold_mb == -10.0
        assert analyzer.collection_growth_threshold == -5
        assert analyzer.check_interval_seconds == 30


class TestAnalyzeMemoryGrowth:
    """Test analyze_memory_growth method."""

    def test_returns_empty_when_no_growth(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        alerts = analyzer.analyze_memory_growth(current, previous)

        assert alerts == []

    def test_returns_empty_when_growth_below_threshold(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=149.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        alerts = analyzer.analyze_memory_growth(current, previous)

        assert alerts == []

    def test_returns_alert_when_growth_exceeds_threshold(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=200.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        alerts = analyzer.analyze_memory_growth(current, previous)

        assert len(alerts) == 1
        assert alerts[0]["type"] == "memory_growth"
        assert alerts[0]["severity"] == "warning"
        assert "Memory grew by 100.0MB in 60s" in alerts[0]["message"]
        assert alerts[0]["current_mb"] == 200.0
        assert alerts[0]["growth_mb"] == 100.0

    def test_returns_alert_when_growth_exactly_at_threshold(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=150.1,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        alerts = analyzer.analyze_memory_growth(current, previous)

        assert len(alerts) == 1
        assert alerts[0]["growth_mb"] == pytest.approx(50.1)

    def test_handles_negative_growth(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=200.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        alerts = analyzer.analyze_memory_growth(current, previous)

        assert alerts == []

    def test_formats_growth_with_one_decimal(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=10.0,
            collection_growth_threshold=100,
            check_interval_seconds=30,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1030.0,
            process_memory_mb=123.456,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        alerts = analyzer.analyze_memory_growth(current, previous)

        assert len(alerts) == 1
        assert "23.5MB" in alerts[0]["message"]

    def test_handles_fractional_memory_values(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=1.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=50.123,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=52.456,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        alerts = analyzer.analyze_memory_growth(current, previous)

        assert len(alerts) == 1
        assert alerts[0]["growth_mb"] == pytest.approx(2.333, rel=1e-3)

    def test_uses_check_interval_in_message(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=10.0,
            collection_growth_threshold=100,
            check_interval_seconds=120,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1120.0,
            process_memory_mb=150.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        alerts = analyzer.analyze_memory_growth(current, previous)

        assert len(alerts) == 1
        assert "in 120s" in alerts[0]["message"]

    def test_handles_zero_memory_values(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=0.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=0.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=0.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        alerts = analyzer.analyze_memory_growth(current, previous)

        assert alerts == []


class TestAnalyzeCollectionGrowth:
    """Test analyze_collection_growth method."""

    def test_returns_empty_when_no_collections(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={},
            task_count=5,
        )

        alerts = analyzer.analyze_collection_growth(current, previous)

        assert alerts == []

    def test_returns_empty_when_no_growth(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 50, "queue": 30},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 50, "queue": 30},
            task_count=5,
        )

        alerts = analyzer.analyze_collection_growth(current, previous)

        assert alerts == []

    def test_returns_empty_when_growth_below_threshold(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 50},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 149},
            task_count=5,
        )

        alerts = analyzer.analyze_collection_growth(current, previous)

        assert alerts == []

    def test_returns_alert_when_growth_exceeds_threshold(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 50},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 200},
            task_count=5,
        )

        alerts = analyzer.analyze_collection_growth(current, previous)

        assert len(alerts) == 1
        assert alerts[0]["type"] == "collection_growth"
        assert alerts[0]["severity"] == "error"
        assert "Collection 'cache' grew by 150 items" in alerts[0]["message"]
        assert alerts[0]["collection"] == "cache"
        assert alerts[0]["current_size"] == 200
        assert alerts[0]["growth"] == 150

    def test_returns_alert_when_growth_exactly_at_threshold(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 50},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 151},
            task_count=5,
        )

        alerts = analyzer.analyze_collection_growth(current, previous)

        assert len(alerts) == 1
        assert alerts[0]["growth"] == 101

    def test_handles_multiple_collections(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 50, "queue": 30, "buffer": 20},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 200, "queue": 180, "buffer": 25},
            task_count=5,
        )

        alerts = analyzer.analyze_collection_growth(current, previous)

        assert len(alerts) == 2
        cache_alert = next(a for a in alerts if a["collection"] == "cache")
        queue_alert = next(a for a in alerts if a["collection"] == "queue")

        assert cache_alert["growth"] == 150
        assert queue_alert["growth"] == 150

    def test_skips_collections_not_in_previous(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 50},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 60, "new_queue": 500},
            task_count=5,
        )

        alerts = analyzer.analyze_collection_growth(current, previous)

        assert alerts == []

    def test_skips_collections_with_zero_current_size(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=0,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 50},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 0},
            task_count=5,
        )

        alerts = analyzer.analyze_collection_growth(current, previous)

        assert alerts == []

    def test_skips_collections_with_negative_current_size(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=0,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 50},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": -10},
            task_count=5,
        )

        alerts = analyzer.analyze_collection_growth(current, previous)

        assert alerts == []

    def test_skips_collections_with_zero_previous_size(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=0,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 0},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 100},
            task_count=5,
        )

        alerts = analyzer.analyze_collection_growth(current, previous)

        assert alerts == []

    def test_skips_collections_with_negative_previous_size(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=0,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": -5},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 100},
            task_count=5,
        )

        alerts = analyzer.analyze_collection_growth(current, previous)

        assert alerts == []

    def test_handles_negative_growth(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 200},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 50},
            task_count=5,
        )

        alerts = analyzer.analyze_collection_growth(current, previous)

        assert alerts == []

    def test_uses_threshold_of_zero(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=0,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 10},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 11},
            task_count=5,
        )

        alerts = analyzer.analyze_collection_growth(current, previous)

        assert len(alerts) == 1
        assert alerts[0]["growth"] == 1

    def test_collection_names_preserved_in_alerts(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=10,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"my_special_cache": 10, "another_queue": 5},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"my_special_cache": 25, "another_queue": 20},
            task_count=5,
        )

        alerts = analyzer.analyze_collection_growth(current, previous)

        assert len(alerts) == 2
        collection_names = {alert["collection"] for alert in alerts}
        assert collection_names == {"my_special_cache", "another_queue"}


class TestIntegration:
    """Integration tests for GrowthAnalyzer."""

    def test_analyze_both_memory_and_collection_growth(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=50.0,
            collection_growth_threshold=100,
            check_interval_seconds=60,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=100.0,
            system_memory_percent=50.0,
            collection_sizes={"cache": 50, "queue": 30},
            task_count=5,
        )

        current = MemorySnapshot(
            timestamp=1060.0,
            process_memory_mb=200.0,
            system_memory_percent=60.0,
            collection_sizes={"cache": 200, "queue": 180},
            task_count=10,
        )

        memory_alerts = analyzer.analyze_memory_growth(current, previous)
        collection_alerts = analyzer.analyze_collection_growth(current, previous)

        assert len(memory_alerts) == 1
        assert len(collection_alerts) == 2
        assert memory_alerts[0]["type"] == "memory_growth"
        assert all(a["type"] == "collection_growth" for a in collection_alerts)

    def test_realistic_scenario_with_mixed_growth(self):
        analyzer = GrowthAnalyzer(
            memory_growth_threshold_mb=25.0,
            collection_growth_threshold=50,
            check_interval_seconds=30,
        )

        previous = MemorySnapshot(
            timestamp=1000.0,
            process_memory_mb=512.0,
            system_memory_percent=45.0,
            collection_sizes={
                "connection_pool": 10,
                "message_queue": 100,
                "price_cache": 500,
                "trade_history": 200,
            },
            task_count=8,
        )

        current = MemorySnapshot(
            timestamp=1030.0,
            process_memory_mb=550.0,
            system_memory_percent=48.0,
            collection_sizes={
                "connection_pool": 12,
                "message_queue": 180,
                "price_cache": 520,
                "trade_history": 199,
            },
            task_count=12,
        )

        memory_alerts = analyzer.analyze_memory_growth(current, previous)
        collection_alerts = analyzer.analyze_collection_growth(current, previous)

        assert len(memory_alerts) == 1
        assert memory_alerts[0]["growth_mb"] == 38.0

        assert len(collection_alerts) == 1
        assert collection_alerts[0]["collection"] == "message_queue"
        assert collection_alerts[0]["growth"] == 80
