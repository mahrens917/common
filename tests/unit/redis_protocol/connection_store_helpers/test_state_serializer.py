"""Tests for state serializer module."""

from __future__ import annotations

import json
import time

from common.connection_state import ConnectionState
from common.redis_protocol.connection_store_helpers.state_serializer import (
    deserialize_state_info,
    parse_all_states,
)


class TestDeserializeStateInfo:
    """Tests for deserialize_state_info function."""

    def test_deserializes_valid_json(self) -> None:
        """Deserializes valid state JSON."""
        timestamp = time.time()
        state_json = json.dumps(
            {
                "service_name": "test",
                "state": "connected",
                "timestamp": timestamp,
                "in_reconnection": False,
            }
        )

        result = deserialize_state_info("test", state_json)

        assert result is not None
        assert result.service_name == "test"
        assert result.state == ConnectionState.CONNECTED
        assert result.in_reconnection is False

    def test_returns_none_for_invalid_json(self) -> None:
        """Returns None for invalid JSON."""
        result = deserialize_state_info("test", "not valid json")

        assert result is None

    def test_returns_none_for_invalid_state_enum(self) -> None:
        """Returns None when state cannot be converted to enum."""
        state_json = json.dumps(
            {
                "service_name": "test",
                "state": "invalid_state_value",
                "timestamp": time.time(),
                "in_reconnection": False,
            }
        )

        result = deserialize_state_info("test", state_json)

        assert result is None


class TestParseAllStates:
    """Tests for parse_all_states function."""

    def test_parses_valid_states(self) -> None:
        """Parses valid state entries."""
        timestamp = time.time()
        all_states = {
            "svc1": json.dumps(
                {
                    "service_name": "svc1",
                    "state": "connected",
                    "timestamp": timestamp,
                    "in_reconnection": False,
                }
            ),
            "svc2": json.dumps(
                {
                    "service_name": "svc2",
                    "state": "disconnected",
                    "timestamp": timestamp,
                    "in_reconnection": True,
                }
            ),
        }

        result = parse_all_states(all_states)

        assert len(result) == 2
        assert "svc1" in result
        assert "svc2" in result
        assert result["svc1"].state == ConnectionState.CONNECTED
        assert result["svc2"].state == ConnectionState.DISCONNECTED

    def test_skips_invalid_entries(self) -> None:
        """Skips entries that cannot be parsed."""
        timestamp = time.time()
        all_states = {
            "valid": json.dumps(
                {
                    "service_name": "valid",
                    "state": "connected",
                    "timestamp": timestamp,
                    "in_reconnection": False,
                }
            ),
            "invalid": "not valid json",
        }

        result = parse_all_states(all_states)

        assert len(result) == 1
        assert "valid" in result
        assert "invalid" not in result

    def test_returns_empty_for_empty_input(self) -> None:
        """Returns empty dict for empty input."""
        result = parse_all_states({})

        assert result == {}
