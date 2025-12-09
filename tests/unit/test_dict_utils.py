"""Tests for common dict_utils module."""

from __future__ import annotations

import pytest

from src.common.dict_utils import mapping_bool, mapping_str


class TestMappingBool:
    """Tests for mapping_bool function."""

    def test_returns_false_for_none_mapping(self) -> None:
        """mapping_bool returns False when mapping is None."""
        assert mapping_bool(None, "key") is False

    def test_returns_false_for_empty_mapping(self) -> None:
        """mapping_bool returns False when mapping is empty."""
        assert mapping_bool({}, "key") is False

    def test_returns_false_for_missing_key(self) -> None:
        """mapping_bool returns False when key is missing."""
        assert mapping_bool({"other": True}, "key") is False

    def test_returns_false_for_none_value(self) -> None:
        """mapping_bool returns False when value is None."""
        assert mapping_bool({"key": None}, "key") is False

    def test_returns_true_for_true_boolean(self) -> None:
        """mapping_bool returns True for boolean True value."""
        assert mapping_bool({"key": True}, "key") is True

    def test_returns_false_for_false_boolean(self) -> None:
        """mapping_bool returns False for boolean False value."""
        assert mapping_bool({"key": False}, "key") is False

    def test_returns_true_for_string_true(self) -> None:
        """mapping_bool returns True for string 'true'."""
        assert mapping_bool({"key": "true"}, "key") is True

    def test_returns_true_for_string_true_uppercase(self) -> None:
        """mapping_bool returns True for string 'TRUE'."""
        assert mapping_bool({"key": "TRUE"}, "key") is True

    def test_returns_true_for_string_true_mixed_case(self) -> None:
        """mapping_bool returns True for string 'True'."""
        assert mapping_bool({"key": "True"}, "key") is True

    def test_returns_false_for_string_false(self) -> None:
        """mapping_bool returns False for string 'false'."""
        assert mapping_bool({"key": "false"}, "key") is False

    def test_returns_false_for_non_true_string(self) -> None:
        """mapping_bool returns False for non-'true' strings."""
        assert mapping_bool({"key": "yes"}, "key") is False
        assert mapping_bool({"key": "1"}, "key") is False


class TestMappingStr:
    """Tests for mapping_str function."""

    def test_returns_default_for_none_mapping(self) -> None:
        """mapping_str returns default when mapping is None."""
        assert mapping_str(None, "key") == ""
        assert mapping_str(None, "key", "default") == "default"

    def test_returns_default_for_empty_mapping(self) -> None:
        """mapping_str returns default when mapping is empty."""
        assert mapping_str({}, "key") == ""
        assert mapping_str({}, "key", "default") == "default"

    def test_returns_default_for_missing_key(self) -> None:
        """mapping_str returns default when key is missing."""
        assert mapping_str({"other": "value"}, "key") == ""
        assert mapping_str({"other": "value"}, "key", "default") == "default"

    def test_returns_default_for_none_value(self) -> None:
        """mapping_str returns default when value is None."""
        assert mapping_str({"key": None}, "key") == ""
        assert mapping_str({"key": None}, "key", "default") == "default"

    def test_returns_string_value(self) -> None:
        """mapping_str returns string value when present."""
        assert mapping_str({"key": "value"}, "key") == "value"

    def test_coerces_int_to_string(self) -> None:
        """mapping_str coerces int to string."""
        assert mapping_str({"key": 123}, "key") == "123"

    def test_coerces_float_to_string(self) -> None:
        """mapping_str coerces float to string."""
        assert mapping_str({"key": 1.5}, "key") == "1.5"

    def test_coerces_bool_to_string(self) -> None:
        """mapping_str coerces bool to string."""
        assert mapping_str({"key": True}, "key") == "True"
        assert mapping_str({"key": False}, "key") == "False"

    def test_empty_string_default(self) -> None:
        """mapping_str uses empty string as default when not specified."""
        assert mapping_str(None, "key") == ""
