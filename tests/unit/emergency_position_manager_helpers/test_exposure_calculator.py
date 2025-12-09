"""Tests for exposure calculator."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.common.emergency_position_manager_helpers.exposure_calculator import (
    calculate_total_exposure,
    get_sorted_high_risk_positions,
    should_reduce_exposure,
)


class TestCalculateTotalExposure:
    """Tests for calculate_total_exposure function."""

    def test_calculates_sum_of_monitored_positions(self) -> None:
        """Calculates sum of market values for monitored positions."""
        position1 = MagicMock()
        position1.ticker = "TICKER-A"
        position1.market_value_cents = 1000

        position2 = MagicMock()
        position2.ticker = "TICKER-B"
        position2.market_value_cents = 2000

        positions = [position1, position2]
        monitored_positions = {"TICKER-A": {}, "TICKER-B": {}}

        result = calculate_total_exposure(positions, monitored_positions)

        assert result == 3000

    def test_ignores_unmonitored_positions(self) -> None:
        """Ignores positions not in monitored_positions."""
        position1 = MagicMock()
        position1.ticker = "TICKER-A"
        position1.market_value_cents = 1000

        position2 = MagicMock()
        position2.ticker = "TICKER-B"
        position2.market_value_cents = 2000

        positions = [position1, position2]
        monitored_positions = {"TICKER-A": {}}  # Only TICKER-A is monitored

        result = calculate_total_exposure(positions, monitored_positions)

        assert result == 1000

    def test_uses_absolute_value(self) -> None:
        """Uses absolute value of market_value_cents."""
        position1 = MagicMock()
        position1.ticker = "TICKER-A"
        position1.market_value_cents = -1500

        position2 = MagicMock()
        position2.ticker = "TICKER-B"
        position2.market_value_cents = 500

        positions = [position1, position2]
        monitored_positions = {"TICKER-A": {}, "TICKER-B": {}}

        result = calculate_total_exposure(positions, monitored_positions)

        assert result == 2000

    def test_returns_zero_for_empty_positions(self) -> None:
        """Returns zero for empty positions list."""
        result = calculate_total_exposure([], {"TICKER-A": {}})

        assert result == 0

    def test_returns_zero_when_no_positions_monitored(self) -> None:
        """Returns zero when no positions are monitored."""
        position = MagicMock()
        position.ticker = "TICKER-A"
        position.market_value_cents = 1000

        result = calculate_total_exposure([position], {})

        assert result == 0


class TestShouldReduceExposure:
    """Tests for should_reduce_exposure function."""

    def test_returns_true_when_exceeds_max(self) -> None:
        """Returns True when exposure exceeds max."""
        assert should_reduce_exposure(total_exposure=15000, max_exposure=10000) is True

    def test_returns_false_when_below_max(self) -> None:
        """Returns False when exposure is below max."""
        assert should_reduce_exposure(total_exposure=5000, max_exposure=10000) is False

    def test_returns_false_when_equal_to_max(self) -> None:
        """Returns False when exposure equals max."""
        assert should_reduce_exposure(total_exposure=10000, max_exposure=10000) is False

    def test_returns_true_when_max_is_zero(self) -> None:
        """Returns True when max_exposure is zero and total is positive."""
        assert should_reduce_exposure(total_exposure=1, max_exposure=0) is True

    def test_returns_false_when_both_zero(self) -> None:
        """Returns False when both values are zero."""
        assert should_reduce_exposure(total_exposure=0, max_exposure=0) is False


class TestGetSortedHighRiskPositions:
    """Tests for get_sorted_high_risk_positions function."""

    def test_filters_high_risk_positions(self) -> None:
        """Filters to only high-risk positions."""
        assessment1 = MagicMock()
        assessment1.requires_closure = True
        assessment1.risk_score = 0.8

        assessment2 = MagicMock()
        assessment2.requires_closure = False
        assessment2.risk_score = 0.3

        result = get_sorted_high_risk_positions([assessment1, assessment2])

        assert len(result) == 1
        assert result[0] is assessment1

    def test_sorts_by_risk_score_descending(self) -> None:
        """Sorts high-risk positions by risk_score descending."""
        assessment1 = MagicMock()
        assessment1.requires_closure = True
        assessment1.risk_score = 0.5

        assessment2 = MagicMock()
        assessment2.requires_closure = True
        assessment2.risk_score = 0.9

        assessment3 = MagicMock()
        assessment3.requires_closure = True
        assessment3.risk_score = 0.7

        result = get_sorted_high_risk_positions([assessment1, assessment2, assessment3])

        assert len(result) == 3
        assert result[0].risk_score == 0.9
        assert result[1].risk_score == 0.7
        assert result[2].risk_score == 0.5

    def test_returns_empty_list_when_no_high_risk(self) -> None:
        """Returns empty list when no high-risk positions."""
        assessment = MagicMock()
        assessment.requires_closure = False
        assessment.risk_score = 0.3

        result = get_sorted_high_risk_positions([assessment])

        assert result == []

    def test_returns_empty_list_for_empty_input(self) -> None:
        """Returns empty list for empty input."""
        result = get_sorted_high_risk_positions([])

        assert result == []

    def test_handles_equal_risk_scores(self) -> None:
        """Handles positions with equal risk scores."""
        assessment1 = MagicMock()
        assessment1.requires_closure = True
        assessment1.risk_score = 0.8

        assessment2 = MagicMock()
        assessment2.requires_closure = True
        assessment2.risk_score = 0.8

        result = get_sorted_high_risk_positions([assessment1, assessment2])

        assert len(result) == 2
        assert all(a.risk_score == 0.8 for a in result)
