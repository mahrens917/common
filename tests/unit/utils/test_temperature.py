"""Tests for common.utils.temperature module."""

from __future__ import annotations

import math

import pytest

from common.utils.temperature import celsius_to_fahrenheit


class TestCelsiusToFahrenheit:
    """Tests for celsius_to_fahrenheit function."""

    def test_zero_celsius(self) -> None:
        assert celsius_to_fahrenheit(0.0) == pytest.approx(32.0)

    def test_boiling_point(self) -> None:
        assert celsius_to_fahrenheit(100.0) == pytest.approx(212.0)

    def test_negative_temperature(self) -> None:
        assert celsius_to_fahrenheit(-40.0) == pytest.approx(-40.0)

    def test_none_returns_nan(self) -> None:
        result = celsius_to_fahrenheit(None)
        assert math.isnan(result)

    def test_nan_returns_nan(self) -> None:
        result = celsius_to_fahrenheit(float("nan"))
        assert math.isnan(result)

    def test_integer_input(self) -> None:
        assert celsius_to_fahrenheit(25) == pytest.approx(77.0)
