"""Tests for batch collection module."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from src.common.redis_protocol.batch_manager_helpers.collection import BatchCollector

EXPECTED_BATCH_SIZE = 2


class TestBatchCollector:
    """Tests for BatchCollector class."""

    def test_init_stores_batch_size(self) -> None:
        """Stores batch size."""
        collector = BatchCollector[str](batch_size=10, name="test")

        assert collector.batch_size == 10

    def test_init_stores_name(self) -> None:
        """Stores name."""
        collector = BatchCollector[str](batch_size=10, name="test_collector")

        assert collector.name == "test_collector"

    def test_init_creates_empty_batch(self) -> None:
        """Creates empty current batch."""
        collector = BatchCollector[str](batch_size=10, name="test")

        assert collector.current_batch == []

    def test_init_no_start_time(self) -> None:
        """Batch start time is None initially."""
        collector = BatchCollector[str](batch_size=10, name="test")

        assert collector.batch_start_time is None


class TestAddItem:
    """Tests for add_item method."""

    def test_adds_item_to_batch(self) -> None:
        """Adds item to current batch."""
        collector = BatchCollector[str](batch_size=10, name="test")

        collector.add_item("item1")

        assert "item1" in collector.current_batch

    def test_returns_false_when_below_threshold(self) -> None:
        """Returns False when batch size below threshold."""
        collector = BatchCollector[str](batch_size=10, name="test")

        result = collector.add_item("item1")

        assert result is False

    def test_returns_true_when_threshold_reached(self) -> None:
        """Returns True when batch size threshold reached."""
        collector = BatchCollector[str](batch_size=3, name="test")
        collector.add_item("item1")
        collector.add_item("item2")

        result = collector.add_item("item3")

        assert result is True

    def test_sets_start_time_on_first_item(self) -> None:
        """Sets batch start time on first item."""
        collector = BatchCollector[str](batch_size=10, name="test")
        assert collector.batch_start_time is None

        before = time.time()
        collector.add_item("item1")
        after = time.time()

        assert collector.batch_start_time is not None
        assert before <= collector.batch_start_time <= after

    def test_does_not_reset_start_time_on_subsequent_items(self) -> None:
        """Does not reset start time on subsequent items."""
        collector = BatchCollector[str](batch_size=10, name="test")
        collector.add_item("item1")
        first_start_time = collector.batch_start_time

        collector.add_item("item2")

        assert collector.batch_start_time == first_start_time


class TestGetBatch:
    """Tests for get_batch method."""

    def test_returns_current_batch(self) -> None:
        """Returns current batch items."""
        collector = BatchCollector[str](batch_size=10, name="test")
        collector.add_item("item1")
        collector.add_item("item2")

        batch = collector.get_batch()

        assert batch == ["item1", "item2"]

    def test_clears_current_batch(self) -> None:
        """Clears current batch after get."""
        collector = BatchCollector[str](batch_size=10, name="test")
        collector.add_item("item1")
        collector.get_batch()

        assert collector.current_batch == []

    def test_resets_start_time(self) -> None:
        """Resets batch start time after get."""
        collector = BatchCollector[str](batch_size=10, name="test")
        collector.add_item("item1")
        collector.get_batch()

        assert collector.batch_start_time is None

    def test_returns_empty_list_when_no_items(self) -> None:
        """Returns empty list when no items."""
        collector = BatchCollector[str](batch_size=10, name="test")

        batch = collector.get_batch()

        assert batch == []


class TestGetBatchMetrics:
    """Tests for get_batch_metrics method."""

    def test_returns_batch_size(self) -> None:
        """Returns current batch size."""
        collector = BatchCollector[str](batch_size=10, name="test")
        collector.add_item("item1")
        collector.add_item("item2")

        batch_size, _ = collector.get_batch_metrics()

        assert batch_size == EXPECTED_BATCH_SIZE

    def test_returns_batch_time(self) -> None:
        """Returns batch time since first item."""
        collector = BatchCollector[str](batch_size=10, name="test")
        collector.add_item("item1")

        _, batch_time = collector.get_batch_metrics()

        assert batch_time >= 0.0

    def test_returns_near_zero_time_when_no_items(self) -> None:
        """Returns near-zero time when no items (no start time)."""
        collector = BatchCollector[str](batch_size=10, name="test")

        _, batch_time = collector.get_batch_metrics()

        # When no start time, time.time() - time.time() should be ~0
        # May be slightly negative due to floating point timing
        assert abs(batch_time) < 0.1  # Should be nearly instant


class TestHasItems:
    """Tests for has_items method."""

    def test_returns_false_when_empty(self) -> None:
        """Returns False when batch is empty."""
        collector = BatchCollector[str](batch_size=10, name="test")

        assert collector.has_items() is False

    def test_returns_true_when_has_items(self) -> None:
        """Returns True when batch has items."""
        collector = BatchCollector[str](batch_size=10, name="test")
        collector.add_item("item1")

        assert collector.has_items() is True


class TestClear:
    """Tests for clear method."""

    def test_clears_current_batch(self) -> None:
        """Clears current batch."""
        collector = BatchCollector[str](batch_size=10, name="test")
        collector.add_item("item1")
        collector.add_item("item2")

        collector.clear()

        assert collector.current_batch == []

    def test_resets_start_time(self) -> None:
        """Resets batch start time."""
        collector = BatchCollector[str](batch_size=10, name="test")
        collector.add_item("item1")

        collector.clear()

        assert collector.batch_start_time is None


class TestGenericType:
    """Tests for generic type support."""

    def test_works_with_int_type(self) -> None:
        """Works with int type."""
        collector = BatchCollector[int](batch_size=10, name="test")
        collector.add_item(1)
        collector.add_item(2)

        batch = collector.get_batch()

        assert batch == [1, 2]

    def test_works_with_dict_type(self) -> None:
        """Works with dict type."""
        collector = BatchCollector[dict](batch_size=10, name="test")
        collector.add_item({"key": "value1"})
        collector.add_item({"key": "value2"})

        batch = collector.get_batch()

        assert batch == [{"key": "value1"}, {"key": "value2"}]
