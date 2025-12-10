"""Tests for state persistence."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from common.daily_max_state_helpers.state_persistence import StatePersistence


class TestStatePersistence:
    """Tests for StatePersistence class."""

    def test_init_stores_state_reference(self) -> None:
        """StatePersistence stores state reference."""
        state = {"max_temp_c": 25.5, "timestamp": None}
        persistence = StatePersistence(state)
        assert persistence._state is state

    def test_reset_for_new_day_calls_state_manager(self) -> None:
        """reset_for_new_day delegates to StateManager."""
        state = {
            "max_temp_c": 25.5,
            "precision": 0.1,
            "source": "test",
            "timestamp": datetime.now(),
            "hourly_max_temp_c": 24.0,
            "hourly_timestamp": datetime.now(),
        }
        persistence = StatePersistence(state)

        with patch(
            "common.daily_max_state_helpers.state_manager.StateManager.reset_for_new_day"
        ) as mock_reset:
            persistence.reset_for_new_day()
            mock_reset.assert_called_once_with(state)

    def test_get_state_dict_calls_state_manager(self) -> None:
        """get_state_dict delegates to StateManager."""
        state = {
            "max_temp_c": 25.5,
            "precision": 0.1,
            "source": "test",
            "timestamp": datetime.now(),
            "hourly_max_temp_c": 24.0,
            "hourly_timestamp": datetime.now(),
        }
        persistence = StatePersistence(state)

        with patch(
            "common.daily_max_state_helpers.state_manager.StateManager.get_state_dict"
        ) as mock_get:
            mock_get.return_value = {"serialized": True}
            result = persistence.get_state_dict()
            mock_get.assert_called_once_with(state)
            assert result == {"serialized": True}

    def test_load_from_state_dict_calls_state_manager(self) -> None:
        """load_from_state_dict delegates to StateManager."""
        state = {"max_temp_c": None}
        state_dict = {"max_temp_c": 25.5}
        persistence = StatePersistence(state)

        with patch(
            "common.daily_max_state_helpers.state_manager.StateManager.load_from_state_dict"
        ) as mock_load:
            persistence.load_from_state_dict(state_dict)
            mock_load.assert_called_once_with(state, state_dict)

    def test_get_state_dict_returns_serializable_dict(self) -> None:
        """get_state_dict returns a serializable dictionary."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0)
        state = {
            "max_temp_c": 25.5,
            "precision": 0.1,
            "source": "test_source",
            "timestamp": timestamp,
            "hourly_max_temp_c": 24.0,
            "hourly_timestamp": timestamp,
        }
        persistence = StatePersistence(state)

        result = persistence.get_state_dict()

        assert result["max_temp_c"] == 25.5
        assert result["precision"] == 0.1
        assert result["source"] == "test_source"
        assert result["timestamp"] == timestamp.isoformat()
        assert result["hourly_max_temp_c"] == 24.0
        assert result["hourly_timestamp"] == timestamp.isoformat()
        assert result["has_data"] is True

    def test_get_state_dict_with_no_data(self) -> None:
        """get_state_dict handles no data case."""
        state = {
            "max_temp_c": float("-inf"),
            "precision": None,
            "source": None,
            "timestamp": None,
            "hourly_max_temp_c": float("-inf"),
            "hourly_timestamp": None,
        }
        persistence = StatePersistence(state)

        result = persistence.get_state_dict()

        assert result["max_temp_c"] == float("-inf")
        assert result["timestamp"] is None
        assert result["has_data"] is False

    def test_reset_for_new_day_resets_all_fields(self) -> None:
        """reset_for_new_day resets all state fields."""
        state = {
            "max_temp_c": 25.5,
            "precision": 0.1,
            "source": "test",
            "timestamp": datetime.now(),
            "hourly_max_temp_c": 24.0,
            "hourly_timestamp": datetime.now(),
        }
        persistence = StatePersistence(state)

        persistence.reset_for_new_day()

        assert state["max_temp_c"] == float("-inf")
        assert state["precision"] is None
        assert state["source"] is None
        assert state["timestamp"] is None
        assert state["hourly_max_temp_c"] == float("-inf")
        assert state["hourly_timestamp"] is None

    def test_load_from_state_dict_restores_state(self) -> None:
        """load_from_state_dict restores state from dict."""
        state = {
            "max_temp_c": float("-inf"),
            "precision": None,
            "source": None,
            "timestamp": None,
            "hourly_max_temp_c": float("-inf"),
            "hourly_timestamp": None,
        }
        state_dict = {
            "max_temp_c": 25.5,
            "precision": 0.1,
            "source": "restored_source",
            "timestamp": "2025-01-15T12:00:00",
            "hourly_max_temp_c": 24.0,
            "hourly_timestamp": "2025-01-15T11:00:00",
        }
        persistence = StatePersistence(state)

        persistence.load_from_state_dict(state_dict)

        assert state["max_temp_c"] == 25.5
        assert state["precision"] == 0.1
        assert state["source"] == "restored_source"
        assert state["timestamp"] == datetime(2025, 1, 15, 12, 0, 0)
        assert state["hourly_max_temp_c"] == 24.0
        assert state["hourly_timestamp"] == datetime(2025, 1, 15, 11, 0, 0)

    def test_load_from_state_dict_with_missing_fields(self) -> None:
        """load_from_state_dict handles missing fields with defaults."""
        state = {
            "max_temp_c": None,
            "precision": None,
            "source": None,
            "timestamp": None,
            "hourly_max_temp_c": None,
            "hourly_timestamp": None,
        }
        state_dict = {}  # Empty dict
        persistence = StatePersistence(state)

        persistence.load_from_state_dict(state_dict)

        assert state["max_temp_c"] == float("-inf")
        assert state["timestamp"] is None
        assert state["hourly_max_temp_c"] == float("-inf")
        assert state["hourly_timestamp"] is None
