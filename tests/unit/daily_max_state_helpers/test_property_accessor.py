"""Tests for property accessor."""

from __future__ import annotations

import pytest

from src.common.daily_max_state_helpers.property_accessor import PropertyAccessor

DEFAULT_TEST_MAX_TEMP_C = 30.0
DEFAULT_TEST_HOURLY_MAX_TEMP_C = 4.0


class TestPropertyAccessor:
    """Tests for PropertyAccessor class."""

    def test_init_stores_state(self) -> None:
        """PropertyAccessor stores state reference."""
        state = {
            "max_temp_c": None,
            "precision": None,
            "source": None,
            "timestamp": None,
            "hourly_max_temp_c": None,
            "hourly_timestamp": None,
        }
        accessor = PropertyAccessor(state)
        assert accessor.max_temp_c is None

    def test_getattr_returns_state_value(self) -> None:
        """__getattr__ returns value from state."""
        state = {
            "max_temp_c": 25.5,
            "precision": 0.1,
            "source": "test_source",
            "timestamp": 1234567890,
            "hourly_max_temp_c": 24.0,
            "hourly_timestamp": 1234567800,
        }
        accessor = PropertyAccessor(state)
        assert accessor.max_temp_c == 25.5
        assert accessor.precision == 0.1
        assert accessor.source == "test_source"
        assert accessor.timestamp == 1234567890
        assert accessor.hourly_max_temp_c == 24.0
        assert accessor.hourly_timestamp == 1234567800

    def test_setattr_updates_state(self) -> None:
        """__setattr__ updates state value."""
        state = {
            "max_temp_c": None,
            "precision": None,
            "source": None,
            "timestamp": None,
            "hourly_max_temp_c": None,
            "hourly_timestamp": None,
        }
        accessor = PropertyAccessor(state)
        accessor.max_temp_c = DEFAULT_TEST_MAX_TEMP_C
        assert state["max_temp_c"] == DEFAULT_TEST_MAX_TEMP_C
        assert accessor.max_temp_c == DEFAULT_TEST_MAX_TEMP_C

    def test_getattr_raises_for_private_attribute(self) -> None:
        """__getattr__ raises AttributeError for private attributes."""
        state = {"max_temp_c": None}
        accessor = PropertyAccessor(state)
        with pytest.raises(AttributeError, match="has no attribute '_private'"):
            _ = accessor._private

    def test_getattr_raises_for_unknown_attribute(self) -> None:
        """__getattr__ raises AttributeError for unknown attributes."""
        state = {"max_temp_c": None}
        accessor = PropertyAccessor(state)
        with pytest.raises(AttributeError, match="has no attribute 'unknown'"):
            _ = accessor.unknown

    def test_setattr_raises_for_unknown_attribute(self) -> None:
        """__setattr__ raises AttributeError for unknown attributes."""
        state = {"max_temp_c": None}
        accessor = PropertyAccessor(state)
        with pytest.raises(AttributeError, match="has no attribute 'unknown'"):
            accessor.unknown = "value"

    def test_setattr_allows_private_attributes(self) -> None:
        """__setattr__ allows setting private attributes on object."""
        state = {"max_temp_c": None}
        accessor = PropertyAccessor(state)
        # This should set on the object itself, not state
        accessor._custom = "value"
        assert accessor._custom == "value"

    def test_all_allowed_keys_accessible(self) -> None:
        """All allowed keys can be accessed."""
        state = {
            "max_temp_c": 1.0,
            "precision": 2.0,
            "source": "src",
            "timestamp": 3,
            "hourly_max_temp_c": DEFAULT_TEST_HOURLY_MAX_TEMP_C,
            "hourly_timestamp": 5,
        }
        accessor = PropertyAccessor(state)
        # Access all keys - should not raise
        assert accessor.max_temp_c == 1.0
        assert accessor.precision == 2.0
        assert accessor.source == "src"
        assert accessor.timestamp == 3
        assert accessor.hourly_max_temp_c == DEFAULT_TEST_HOURLY_MAX_TEMP_C
        assert accessor.hourly_timestamp == 5

    def test_setattr_updates_all_allowed_keys(self) -> None:
        """All allowed keys can be set."""
        state = {
            "max_temp_c": None,
            "precision": None,
            "source": None,
            "timestamp": None,
            "hourly_max_temp_c": None,
            "hourly_timestamp": None,
        }
        accessor = PropertyAccessor(state)
        accessor.max_temp_c = 1.0
        accessor.precision = 2.0
        accessor.source = "src"
        accessor.timestamp = 3
        accessor.hourly_max_temp_c = DEFAULT_TEST_HOURLY_MAX_TEMP_C
        accessor.hourly_timestamp = 5
        assert state["max_temp_c"] == 1.0
        assert state["precision"] == 2.0
        assert state["source"] == "src"
        assert state["timestamp"] == 3
        assert state["hourly_max_temp_c"] == DEFAULT_TEST_HOURLY_MAX_TEMP_C
        assert state["hourly_timestamp"] == 5
