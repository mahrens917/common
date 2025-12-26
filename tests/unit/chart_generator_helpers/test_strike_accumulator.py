"""Tests for chart_generator_helpers.strike_accumulator module."""

import pytest

from common.chart_generator_helpers.strike_accumulator import StrikeAccumulator


class TestStrikeAccumulatorAccumulateStrikeValues:
    """Tests for accumulate_strike_values method."""

    def test_greater_strike_type_adds_floor(self) -> None:
        """Test 'greater' strike type adds floor strike."""
        accumulator = StrikeAccumulator()
        strikes: set[float] = set()

        accumulator.accumulate_strike_values("greater", 100.0, 200.0, strikes)

        assert strikes == {100.0}

    def test_less_strike_type_adds_cap(self) -> None:
        """Test 'less' strike type adds cap strike."""
        accumulator = StrikeAccumulator()
        strikes: set[float] = set()

        accumulator.accumulate_strike_values("less", 100.0, 200.0, strikes)

        assert strikes == {200.0}

    def test_between_strike_type_adds_both(self) -> None:
        """Test 'between' strike type adds both strikes."""
        accumulator = StrikeAccumulator()
        strikes: set[float] = set()

        accumulator.accumulate_strike_values("between", 100.0, 200.0, strikes)

        assert strikes == {100.0, 200.0}

    def test_other_strike_type_adds_both(self) -> None:
        """Test other strike type adds both strikes."""
        accumulator = StrikeAccumulator()
        strikes: set[float] = set()

        accumulator.accumulate_strike_values("other", 100.0, 200.0, strikes)

        assert strikes == {100.0, 200.0}

    def test_handles_none_floor_strike(self) -> None:
        """Test handles None floor strike."""
        accumulator = StrikeAccumulator()
        strikes: set[float] = set()

        accumulator.accumulate_strike_values("greater", None, 200.0, strikes)

        assert strikes == set()

    def test_handles_none_cap_strike(self) -> None:
        """Test handles None cap strike."""
        accumulator = StrikeAccumulator()
        strikes: set[float] = set()

        accumulator.accumulate_strike_values("less", 100.0, None, strikes)

        assert strikes == set()

    def test_handles_both_none(self) -> None:
        """Test handles both strikes None."""
        accumulator = StrikeAccumulator()
        strikes: set[float] = set()

        accumulator.accumulate_strike_values("between", None, None, strikes)

        assert strikes == set()

    def test_accumulates_to_existing_set(self) -> None:
        """Test accumulates to existing set."""
        accumulator = StrikeAccumulator()
        strikes: set[float] = {50.0}

        accumulator.accumulate_strike_values("between", 100.0, 200.0, strikes)

        assert strikes == {50.0, 100.0, 200.0}


class TestStrikeAccumulatorAddFloorStrike:
    """Tests for _add_floor_strike static method."""

    def test_adds_floor_strike(self) -> None:
        """Test adds floor strike."""
        strikes: set[float] = set()

        StrikeAccumulator._add_floor_strike(100.0, strikes)

        assert strikes == {100.0}

    def test_ignores_none_floor_strike(self) -> None:
        """Test ignores None floor strike."""
        strikes: set[float] = set()

        StrikeAccumulator._add_floor_strike(None, strikes)

        assert strikes == set()


class TestStrikeAccumulatorAddCapStrike:
    """Tests for _add_cap_strike static method."""

    def test_adds_cap_strike(self) -> None:
        """Test adds cap strike."""
        strikes: set[float] = set()

        StrikeAccumulator._add_cap_strike(200.0, strikes)

        assert strikes == {200.0}

    def test_ignores_none_cap_strike(self) -> None:
        """Test ignores None cap strike."""
        strikes: set[float] = set()

        StrikeAccumulator._add_cap_strike(None, strikes)

        assert strikes == set()


class TestStrikeAccumulatorAddBothStrikes:
    """Tests for _add_both_strikes static method."""

    def test_adds_both_strikes(self) -> None:
        """Test adds both strikes."""
        strikes: set[float] = set()

        StrikeAccumulator._add_both_strikes(100.0, 200.0, strikes)

        assert strikes == {100.0, 200.0}

    def test_adds_only_floor_when_cap_none(self) -> None:
        """Test adds only floor when cap is None."""
        strikes: set[float] = set()

        StrikeAccumulator._add_both_strikes(100.0, None, strikes)

        assert strikes == {100.0}

    def test_adds_only_cap_when_floor_none(self) -> None:
        """Test adds only cap when floor is None."""
        strikes: set[float] = set()

        StrikeAccumulator._add_both_strikes(None, 200.0, strikes)

        assert strikes == {200.0}

    def test_adds_nothing_when_both_none(self) -> None:
        """Test adds nothing when both are None."""
        strikes: set[float] = set()

        StrikeAccumulator._add_both_strikes(None, None, strikes)

        assert strikes == set()
