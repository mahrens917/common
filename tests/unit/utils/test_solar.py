"""Tests for common.utils.solar module."""

from __future__ import annotations

import math
from datetime import date, datetime, time, timezone

import pytest

from common.utils.solar import (
    SolarTimes,
    compute_day_of_year_encoding,
    compute_solar_diurnal,
    compute_solar_diurnal_from_iso,
    compute_solar_times,
)

# New York City coordinates
_NYC_LAT = 40.7128
_NYC_LON = -74.0060

# Equator coordinates
_EQUATOR_LAT = 0.0
_PRIME_MERIDIAN_LON = 0.0

# Arctic coordinates for polar edge cases
_ARCTIC_LAT = 89.0
_ARCTIC_LON = 0.0

_SUMMER_SOLSTICE = date(2024, 6, 21)
_WINTER_SOLSTICE = date(2024, 12, 21)
_SPRING_EQUINOX = date(2024, 3, 20)


class TestComputeSolarTimes:
    """Tests for compute_solar_times."""

    def test_returns_solar_times_named_tuple(self) -> None:
        result = compute_solar_times(_NYC_LAT, _NYC_LON, _SPRING_EQUINOX)
        assert isinstance(result, SolarTimes)
        assert isinstance(result.sunrise, time)
        assert isinstance(result.solar_noon, time)
        assert isinstance(result.sunset, time)

    def test_sunrise_before_noon_before_sunset(self) -> None:
        result = compute_solar_times(_NYC_LAT, _NYC_LON, _SPRING_EQUINOX)
        sunrise_h = result.sunrise.hour + result.sunrise.minute / 60
        noon_h = result.solar_noon.hour + result.solar_noon.minute / 60
        sunset_h = result.sunset.hour + result.sunset.minute / 60
        assert sunrise_h < noon_h < sunset_h

    def test_equator_summer_solstice(self) -> None:
        result = compute_solar_times(_EQUATOR_LAT, _PRIME_MERIDIAN_LON, _SUMMER_SOLSTICE)
        assert result.solar_noon.hour == 12 or (result.solar_noon.hour == 11 and result.solar_noon.minute > 50)

    def test_longer_days_in_summer(self) -> None:
        summer = compute_solar_times(_NYC_LAT, _NYC_LON, _SUMMER_SOLSTICE)
        winter = compute_solar_times(_NYC_LAT, _NYC_LON, _WINTER_SOLSTICE)

        def day_length_hours(st: SolarTimes) -> float:
            sunrise = st.sunrise.hour + st.sunrise.minute / 60
            sunset = st.sunset.hour + st.sunset.minute / 60
            length = sunset - sunrise
            if length < 0:
                length += 24
            return length

        assert day_length_hours(summer) > day_length_hours(winter)


class TestComputeSolarDiurnal:
    """Tests for compute_solar_diurnal."""

    def test_midday_returns_around_half(self) -> None:
        solar = compute_solar_times(_NYC_LAT, _NYC_LON, _SPRING_EQUINOX)
        noon_dt = datetime(2024, 3, 20, solar.solar_noon.hour, solar.solar_noon.minute, tzinfo=timezone.utc)
        result = compute_solar_diurnal(noon_dt, _NYC_LAT, _NYC_LON)
        assert 0.4 < result < 0.6

    def test_before_sunrise_negative(self) -> None:
        early = datetime(2024, 3, 20, 3, 0, tzinfo=timezone.utc)
        result = compute_solar_diurnal(early, _NYC_LAT, _NYC_LON)
        assert result < 0

    def test_after_sunset_greater_than_one(self) -> None:
        late = datetime(2024, 3, 20, 23, 59, tzinfo=timezone.utc)
        result = compute_solar_diurnal(late, _NYC_LAT, _NYC_LON)
        assert result > 1


class TestComputeDayOfYearEncoding:
    """Tests for compute_day_of_year_encoding."""

    def test_returns_sin_cos_tuple(self) -> None:
        dt = datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)
        sin_val, cos_val = compute_day_of_year_encoding(dt)
        assert isinstance(sin_val, float)
        assert isinstance(cos_val, float)

    def test_values_on_unit_circle(self) -> None:
        dt = datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)
        sin_val, cos_val = compute_day_of_year_encoding(dt)
        assert abs(sin_val**2 + cos_val**2 - 1.0) < 1e-9

    def test_jan_1_near_zero_sin(self) -> None:
        dt = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        sin_val, _ = compute_day_of_year_encoding(dt)
        assert abs(sin_val) < 0.02


class TestComputeSolarDiurnalFromIso:
    """Tests for compute_solar_diurnal_from_iso."""

    def test_valid_iso_returns_float(self) -> None:
        result = compute_solar_diurnal_from_iso("2024-03-20T17:00:00Z", _NYC_LAT, _NYC_LON)
        assert result is not None
        assert isinstance(result, float)

    def test_invalid_iso_returns_none(self) -> None:
        result = compute_solar_diurnal_from_iso("not-a-date", _NYC_LAT, _NYC_LON)
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        result = compute_solar_diurnal_from_iso("", _NYC_LAT, _NYC_LON)
        assert result is None

    def test_iso_with_offset(self) -> None:
        result = compute_solar_diurnal_from_iso("2024-03-20T12:00:00+00:00", _NYC_LAT, _NYC_LON)
        assert result is not None
