"""Tests for daily_max_state_helpers.result_generator module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from common.daily_max_state_helpers.result_generator import (
    DailyMaxResult,
    ResultGenerator,
)
from common.exceptions import DataError


class TestDailyMaxResult:
    """Tests for DailyMaxResult dataclass."""

    def test_stores_all_fields(self) -> None:
        """Test stores all fields."""
        now = datetime.now(tz=timezone.utc)
        result = DailyMaxResult(
            max_temp_f=75,
            confidence="HIGH",
            precision_c=0.1,
            source="hourly",
            timestamp=now,
        )

        assert result.max_temp_f == 75
        assert result.confidence == "HIGH"
        assert result.precision_c == 0.1
        assert result.source == "hourly"
        assert result.timestamp == now

    def test_timestamp_defaults_to_none(self) -> None:
        """Test timestamp defaults to None."""
        result = DailyMaxResult(
            max_temp_f=70,
            confidence="MEDIUM",
            precision_c=1.0,
            source="6h",
        )

        assert result.timestamp is None


class TestResultGeneratorGetDailyMaxResult:
    """Tests for get_daily_max_result static method."""

    def test_returns_none_for_invalid_max_temp(self) -> None:
        """Test returns None when max_temp_c is not a number."""
        state = {"max_temp_c": "invalid"}

        result = ResultGenerator.get_daily_max_result(state)

        assert result is None

    def test_returns_none_for_missing_max_temp(self) -> None:
        """Test returns None when max_temp_c is missing."""
        state = {}

        result = ResultGenerator.get_daily_max_result(state)

        assert result is None

    def test_returns_none_for_negative_infinity(self) -> None:
        """Test returns None when max_temp_c is -inf."""
        state = {"max_temp_c": float("-inf")}

        result = ResultGenerator.get_daily_max_result(state)

        assert result is None

    def test_returns_none_for_missing_precision(self) -> None:
        """Test returns None when precision is missing."""
        state = {"max_temp_c": 25.0, "source": "hourly"}

        result = ResultGenerator.get_daily_max_result(state)

        assert result is None

    def test_returns_none_for_missing_source(self) -> None:
        """Test returns None when source is missing."""
        state = {"max_temp_c": 25.0, "precision": 0.1}

        result = ResultGenerator.get_daily_max_result(state)

        assert result is None

    def test_returns_daily_max_result(self) -> None:
        """Test returns DailyMaxResult with valid state."""
        state = {
            "max_temp_c": 24.0,
            "precision": 0.1,
            "source": "hourly",
        }

        with patch("common.daily_max_state_helpers.result_generator._get_cli_temp_f") as mock_get_fn:
            mock_get_fn.return_value = lambda c: int(c * 9 / 5 + 32)
            result = ResultGenerator.get_daily_max_result(state)

            assert result is not None
            assert isinstance(result, DailyMaxResult)
            assert result.max_temp_f == 75  # 24°C = 75°F
            assert result.confidence == "HIGH"
            assert result.precision_c == 0.1
            assert result.source == "hourly"

    def test_includes_timestamp_when_present(self) -> None:
        """Test includes timestamp when present in state."""
        now = datetime.now(tz=timezone.utc)
        state = {
            "max_temp_c": 24.0,
            "precision": 0.1,
            "source": "hourly",
            "timestamp": now,
        }

        with patch("common.daily_max_state_helpers.result_generator._get_cli_temp_f") as mock_get_fn:
            mock_get_fn.return_value = lambda c: int(c * 9 / 5 + 32)
            result = ResultGenerator.get_daily_max_result(state)

            assert result.timestamp == now

    def test_handles_medium_confidence(self) -> None:
        """Test handles MEDIUM confidence for 1.0 precision."""
        state = {
            "max_temp_c": 20.0,
            "precision": 1.0,
            "source": "6h",
        }

        with patch("common.daily_max_state_helpers.result_generator._get_cli_temp_f") as mock_get_fn:
            mock_get_fn.return_value = lambda c: int(c * 9 / 5 + 32)
            result = ResultGenerator.get_daily_max_result(state)

            assert result.confidence == "MEDIUM"


class TestResultGeneratorGetAdjustedTempForRule:
    """Tests for get_adjusted_temp_for_rule static method."""

    def test_raises_for_invalid_max_temp(self) -> None:
        """Test raises DataError when max_temp_c is not a number."""
        state = {"max_temp_c": None}

        with pytest.raises(DataError):
            ResultGenerator.get_adjusted_temp_for_rule(state, "conservative")

    def test_raises_for_negative_infinity(self) -> None:
        """Test raises DataError when max_temp_c is -inf."""
        state = {"max_temp_c": float("-inf")}

        with pytest.raises(DataError):
            ResultGenerator.get_adjusted_temp_for_rule(state, "conservative")

    def test_raises_for_unknown_rule_type(self) -> None:
        """Test raises ValueError for unknown rule type."""
        state = {"max_temp_c": 25.0, "precision": 0.1}

        with pytest.raises(ValueError) as exc_info:
            ResultGenerator.get_adjusted_temp_for_rule(state, "unknown")

        assert "Unknown rule_type" in str(exc_info.value)

    def test_conservative_adds_margin(self) -> None:
        """Test conservative rule adds safety margin."""
        state = {"max_temp_c": 25.0, "precision": 1.0}  # MEDIUM = 0.5°C margin

        with patch("common.daily_max_state_helpers.result_generator._get_cli_temp_f") as mock_get_fn:
            mock_get_fn.return_value = lambda c: int(c * 9 / 5 + 32)
            result = ResultGenerator.get_adjusted_temp_for_rule(state, "conservative")

            # 25.5°C -> 77.9 -> 77°F
            assert result == 77

    def test_aggressive_subtracts_margin(self) -> None:
        """Test aggressive rule subtracts safety margin."""
        state = {"max_temp_c": 25.0, "precision": 1.0}  # MEDIUM = 0.5°C margin

        with patch("common.daily_max_state_helpers.result_generator._get_cli_temp_f") as mock_get_fn:
            mock_get_fn.return_value = lambda c: int(c * 9 / 5 + 32)
            result = ResultGenerator.get_adjusted_temp_for_rule(state, "aggressive")

            # 24.5°C -> 76.1 -> 76°F
            assert result == 76

    def test_high_precision_no_margin(self) -> None:
        """Test HIGH precision has no margin adjustment."""
        state = {"max_temp_c": 25.0, "precision": 0.1}

        with patch("common.daily_max_state_helpers.result_generator._get_cli_temp_f") as mock_get_fn:
            mock_get_fn.return_value = lambda c: int(c * 9 / 5 + 32)
            conservative = ResultGenerator.get_adjusted_temp_for_rule(state, "conservative")
            aggressive = ResultGenerator.get_adjusted_temp_for_rule(state, "aggressive")

            # Both should be the same (no margin)
            assert conservative == aggressive


class TestResultGeneratorGetHourlyOnlyMaxF:
    """Tests for get_hourly_only_max_f static method."""

    def test_returns_none_for_invalid_type(self) -> None:
        """Test returns None when hourly_max_temp_c is not a number."""
        state = {"hourly_max_temp_c": "invalid"}

        result = ResultGenerator.get_hourly_only_max_f(state)

        assert result is None

    def test_returns_none_for_missing_value(self) -> None:
        """Test returns None when hourly_max_temp_c is missing."""
        state = {}

        result = ResultGenerator.get_hourly_only_max_f(state)

        assert result is None

    def test_returns_none_for_negative_infinity(self) -> None:
        """Test returns None when hourly_max_temp_c is -inf."""
        state = {"hourly_max_temp_c": float("-inf")}

        result = ResultGenerator.get_hourly_only_max_f(state)

        assert result is None

    def test_returns_fahrenheit_temperature(self) -> None:
        """Test returns temperature converted to Fahrenheit."""
        state = {"hourly_max_temp_c": 30.0}

        with patch("common.daily_max_state_helpers.result_generator._get_cli_temp_f") as mock_get_fn:
            mock_get_fn.return_value = lambda c: int(c * 9 / 5 + 32)
            result = ResultGenerator.get_hourly_only_max_f(state)

            assert result == 86  # 30°C = 86°F

    def test_handles_zero_celsius(self) -> None:
        """Test handles zero celsius correctly."""
        state = {"hourly_max_temp_c": 0.0}

        with patch("common.daily_max_state_helpers.result_generator._get_cli_temp_f") as mock_get_fn:
            mock_get_fn.return_value = lambda c: int(c * 9 / 5 + 32)
            result = ResultGenerator.get_hourly_only_max_f(state)

            assert result == 32  # 0°C = 32°F
