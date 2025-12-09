"""Tests for state persistence module."""

from __future__ import annotations

import json

from src.common.redis_protocol.connection_store_helpers.state_persistence import (
    try_deserialize_state,
    try_serialize_state,
)


class TestTrySerializeState:
    """Tests for try_serialize_state function."""

    def test_serializes_valid_dict(self) -> None:
        """Serializes valid dict to JSON."""
        state_dict = {"key": "value", "number": 42}

        result = try_serialize_state(state_dict)

        assert result is not None
        assert json.loads(result) == state_dict

    def test_returns_none_for_non_serializable(self) -> None:
        """Returns None for non-serializable content."""
        state_dict = {"func": lambda x: x}

        result = try_serialize_state(state_dict)

        assert result is None


class TestTryDeserializeState:
    """Tests for try_deserialize_state function."""

    def test_deserializes_valid_json(self) -> None:
        """Deserializes valid JSON string."""
        state_json = '{"key": "value", "number": 42}'

        result = try_deserialize_state(state_json)

        assert result == {"key": "value", "number": 42}

    def test_returns_none_for_invalid_json(self) -> None:
        """Returns None for invalid JSON."""
        result = try_deserialize_state("not valid json")

        assert result is None

    def test_returns_none_for_empty_string(self) -> None:
        """Returns None for empty string."""
        result = try_deserialize_state("")

        assert result is None
