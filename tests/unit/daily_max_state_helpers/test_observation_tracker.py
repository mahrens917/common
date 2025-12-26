"""Tests for daily_max_state_helpers.observation_tracker module."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from common.daily_max_state_helpers.observation_tracker import ObservationTracker

# Test constants (data_guard requirement)
TEST_TEMP_C_20 = 20.0
TEST_TEMP_C_25 = 25.0
TEST_TEMP_C_30 = 30.0
TEST_TEMP_INT_20 = 20
TEST_TEMP_INT_25 = 25
TEST_TEMP_INT_30 = 30
TEST_SAFETY_MARGIN = 0.5
TEST_SAFETY_MARGIN_ALT = 0.7
TEST_SAFETY_MARGIN_INVALID = "invalid"
TEST_PRECISION_0_1 = 0.1
TEST_PRECISION_1_0 = 1.0
TEST_SOURCE_HOURLY = "hourly"
TEST_SOURCE_6H = "6h"


class TestObservationTrackerAddHourlyObservation:
    """Tests for add_hourly_observation static method."""

    def test_raises_when_temp_is_none(self) -> None:
        """Test raises ValueError when temp_c is None."""
        state = {"max_temp_c": float("-inf"), "hourly_max_temp_c": float("-inf")}

        with pytest.raises(ValueError) as exc_info:
            ObservationTracker.add_hourly_observation(state, None)

        assert "Temperature cannot be None" in str(exc_info.value)

    def test_uses_current_utc_when_timestamp_is_none(self) -> None:
        """Test uses current UTC time when timestamp is None."""
        state = {
            "max_temp_c": float("-inf"),
            "hourly_max_temp_c": float("-inf"),
            "precision": None,
            "source": None,
            "timestamp": None,
            "hourly_timestamp": None,
        }
        mock_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        with patch("common.time_utils.get_current_utc", return_value=mock_time):
            ObservationTracker.add_hourly_observation(state, TEST_TEMP_C_25)

        assert state["timestamp"] == mock_time
        assert state["hourly_timestamp"] == mock_time

    def test_updates_max_temp_when_new_temp_higher(self) -> None:
        """Test updates max_temp_c when new temperature is higher."""
        now = datetime.now(tz=timezone.utc)
        state = {
            "max_temp_c": TEST_TEMP_C_20,
            "precision": TEST_PRECISION_1_0,
            "source": TEST_SOURCE_6H,
            "timestamp": None,
            "hourly_max_temp_c": float("-inf"),
            "hourly_timestamp": None,
        }

        ObservationTracker.add_hourly_observation(state, TEST_TEMP_C_25, now)

        assert state["max_temp_c"] == TEST_TEMP_C_25
        assert state["precision"] == TEST_PRECISION_0_1
        assert state["source"] == TEST_SOURCE_HOURLY
        assert state["timestamp"] == now

    def test_does_not_update_max_temp_when_new_temp_lower(self) -> None:
        """Test does not update max_temp_c when new temperature is lower."""
        original_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        new_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        state = {
            "max_temp_c": TEST_TEMP_C_30,
            "precision": TEST_PRECISION_0_1,
            "source": TEST_SOURCE_HOURLY,
            "timestamp": original_time,
            "hourly_max_temp_c": TEST_TEMP_C_30,
            "hourly_timestamp": original_time,
        }

        ObservationTracker.add_hourly_observation(state, TEST_TEMP_C_25, new_time)

        # max_temp_c should not change
        assert state["max_temp_c"] == TEST_TEMP_C_30
        assert state["precision"] == TEST_PRECISION_0_1
        assert state["source"] == TEST_SOURCE_HOURLY
        assert state["timestamp"] == original_time

    def test_updates_hourly_max_when_new_temp_higher(self) -> None:
        """Test updates hourly_max_temp_c when new temperature is higher."""
        now = datetime.now(tz=timezone.utc)
        state = {
            "max_temp_c": TEST_TEMP_C_30,
            "precision": TEST_PRECISION_0_1,
            "source": TEST_SOURCE_HOURLY,
            "timestamp": None,
            "hourly_max_temp_c": TEST_TEMP_C_20,
            "hourly_timestamp": None,
        }

        ObservationTracker.add_hourly_observation(state, TEST_TEMP_C_25, now)

        assert state["hourly_max_temp_c"] == TEST_TEMP_C_25
        assert state["hourly_timestamp"] == now

    def test_does_not_update_hourly_max_when_new_temp_lower(self) -> None:
        """Test does not update hourly_max_temp_c when new temperature is lower."""
        original_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        new_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        state = {
            "max_temp_c": TEST_TEMP_C_30,
            "precision": TEST_PRECISION_0_1,
            "source": TEST_SOURCE_HOURLY,
            "timestamp": original_time,
            "hourly_max_temp_c": TEST_TEMP_C_30,
            "hourly_timestamp": original_time,
        }

        ObservationTracker.add_hourly_observation(state, TEST_TEMP_C_20, new_time)

        # hourly_max_temp_c should not change
        assert state["hourly_max_temp_c"] == TEST_TEMP_C_30
        assert state["hourly_timestamp"] == original_time

    def test_updates_both_max_and_hourly_max_for_first_observation(self) -> None:
        """Test updates both max_temp_c and hourly_max_temp_c for first observation."""
        now = datetime.now(tz=timezone.utc)
        state = {
            "max_temp_c": float("-inf"),
            "precision": None,
            "source": None,
            "timestamp": None,
            "hourly_max_temp_c": float("-inf"),
            "hourly_timestamp": None,
        }

        ObservationTracker.add_hourly_observation(state, TEST_TEMP_C_25, now)

        assert state["max_temp_c"] == TEST_TEMP_C_25
        assert state["precision"] == TEST_PRECISION_0_1
        assert state["source"] == TEST_SOURCE_HOURLY
        assert state["timestamp"] == now
        assert state["hourly_max_temp_c"] == TEST_TEMP_C_25
        assert state["hourly_timestamp"] == now


class TestObservationTrackerAdd6hMaximum:
    """Tests for add_6h_maximum static method."""

    def test_raises_when_max_c_is_none(self) -> None:
        """Test raises ValueError when max_c is None."""
        state = {"max_temp_c": float("-inf")}
        metar_config = {}

        with pytest.raises(ValueError) as exc_info:
            ObservationTracker.add_6h_maximum(state, metar_config, None)

        assert "6-hour maximum cannot be None" in str(exc_info.value)

    def test_uses_current_utc_when_window_end_is_none(self) -> None:
        """Test uses current UTC time when window_end is None."""
        state = {
            "max_temp_c": float("-inf"),
            "precision": None,
            "source": None,
            "timestamp": None,
        }
        metar_config = {}
        mock_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        with patch("common.time_utils.get_current_utc", return_value=mock_time):
            ObservationTracker.add_6h_maximum(state, metar_config, TEST_TEMP_INT_25)

        assert state["timestamp"] == mock_time

    def test_applies_safety_margin_from_config(self) -> None:
        """Test applies safety margin from METAR config."""
        now = datetime.now(tz=timezone.utc)
        state = {
            "max_temp_c": float("-inf"),
            "precision": None,
            "source": None,
            "timestamp": None,
        }
        metar_config = {"6h_max": {"safety_margin_celsius": TEST_SAFETY_MARGIN_ALT}}

        ObservationTracker.add_6h_maximum(state, metar_config, TEST_TEMP_INT_25, now)

        # 25 - 0.7 = 24.3
        assert state["max_temp_c"] == 24.3
        assert state["precision"] == TEST_PRECISION_1_0
        assert state["source"] == TEST_SOURCE_6H
        assert state["timestamp"] == now

    def test_uses_default_safety_margin_when_not_in_config(self) -> None:
        """Test uses default safety margin of 0.5 when not in config."""
        now = datetime.now(tz=timezone.utc)
        state = {
            "max_temp_c": float("-inf"),
            "precision": None,
            "source": None,
            "timestamp": None,
        }
        metar_config = {}

        ObservationTracker.add_6h_maximum(state, metar_config, TEST_TEMP_INT_25, now)

        # 25 - 0.5 = 24.5
        assert state["max_temp_c"] == 24.5
        assert state["precision"] == TEST_PRECISION_1_0
        assert state["source"] == TEST_SOURCE_6H
        assert state["timestamp"] == now

    def test_uses_default_safety_margin_when_config_value_invalid(self) -> None:
        """Test uses default safety margin when config value is invalid."""
        now = datetime.now(tz=timezone.utc)
        state = {
            "max_temp_c": float("-inf"),
            "precision": None,
            "source": None,
            "timestamp": None,
        }
        metar_config = {"6h_max": {"safety_margin_celsius": TEST_SAFETY_MARGIN_INVALID}}

        ObservationTracker.add_6h_maximum(state, metar_config, TEST_TEMP_INT_25, now)

        # 25 - 0.5 = 24.5 (default)
        assert state["max_temp_c"] == 24.5

    def test_uses_default_safety_margin_when_6h_max_is_not_dict(self) -> None:
        """Test uses default safety margin when 6h_max is not a dict."""
        now = datetime.now(tz=timezone.utc)
        state = {
            "max_temp_c": float("-inf"),
            "precision": None,
            "source": None,
            "timestamp": None,
        }
        metar_config = {"6h_max": TEST_SAFETY_MARGIN_INVALID}

        ObservationTracker.add_6h_maximum(state, metar_config, TEST_TEMP_INT_25, now)

        # 25 - 0.5 = 24.5 (default)
        assert state["max_temp_c"] == 24.5

    def test_updates_max_temp_when_new_temp_higher_after_margin(self) -> None:
        """Test updates max_temp_c when new temperature is higher after safety margin."""
        now = datetime.now(tz=timezone.utc)
        state = {
            "max_temp_c": TEST_TEMP_C_20,
            "precision": TEST_PRECISION_0_1,
            "source": TEST_SOURCE_HOURLY,
            "timestamp": None,
        }
        metar_config = {"6h_max": {"safety_margin_celsius": TEST_SAFETY_MARGIN}}

        ObservationTracker.add_6h_maximum(state, metar_config, TEST_TEMP_INT_25, now)

        # 25 - 0.5 = 24.5, which is > 20
        assert state["max_temp_c"] == 24.5
        assert state["precision"] == TEST_PRECISION_1_0
        assert state["source"] == TEST_SOURCE_6H
        assert state["timestamp"] == now

    def test_does_not_update_max_temp_when_new_temp_lower_after_margin(self) -> None:
        """Test does not update max_temp_c when new temperature is lower after safety margin."""
        original_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        new_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        state = {
            "max_temp_c": TEST_TEMP_C_30,
            "precision": TEST_PRECISION_0_1,
            "source": TEST_SOURCE_HOURLY,
            "timestamp": original_time,
        }
        metar_config = {"6h_max": {"safety_margin_celsius": TEST_SAFETY_MARGIN}}

        ObservationTracker.add_6h_maximum(state, metar_config, TEST_TEMP_INT_25, new_time)

        # 25 - 0.5 = 24.5, which is < 30
        assert state["max_temp_c"] == TEST_TEMP_C_30
        assert state["precision"] == TEST_PRECISION_0_1
        assert state["source"] == TEST_SOURCE_HOURLY
        assert state["timestamp"] == original_time

    def test_does_not_update_hourly_max(self) -> None:
        """Test does not update hourly_max_temp_c (only updates overall max)."""
        now = datetime.now(tz=timezone.utc)
        state = {
            "max_temp_c": float("-inf"),
            "precision": None,
            "source": None,
            "timestamp": None,
            "hourly_max_temp_c": TEST_TEMP_C_20,
            "hourly_timestamp": None,
        }
        metar_config = {}

        ObservationTracker.add_6h_maximum(state, metar_config, TEST_TEMP_INT_30, now)

        # hourly_max_temp_c should not change
        assert state["hourly_max_temp_c"] == TEST_TEMP_C_20

    def test_handles_6h_max_config_as_none(self) -> None:
        """Test handles when 6h_max config is None."""
        now = datetime.now(tz=timezone.utc)
        state = {
            "max_temp_c": float("-inf"),
            "precision": None,
            "source": None,
            "timestamp": None,
        }
        metar_config = {"6h_max": None}

        ObservationTracker.add_6h_maximum(state, metar_config, TEST_TEMP_INT_25, now)

        # Should use default safety margin 0.5
        assert state["max_temp_c"] == 24.5

    def test_handles_6h_max_config_as_empty_dict(self) -> None:
        """Test handles when 6h_max config is empty dict."""
        now = datetime.now(tz=timezone.utc)
        state = {
            "max_temp_c": float("-inf"),
            "precision": None,
            "source": None,
            "timestamp": None,
        }
        metar_config = {"6h_max": {}}

        ObservationTracker.add_6h_maximum(state, metar_config, TEST_TEMP_INT_25, now)

        # Should use default safety margin 0.5
        assert state["max_temp_c"] == 24.5
