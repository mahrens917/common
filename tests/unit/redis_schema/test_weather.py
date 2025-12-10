"""Tests for src/common/redis_schema/weather.py."""

import pytest

from common.exceptions import ValidationError
from common.redis_schema.weather import (
    WeatherAlertKey,
    WeatherHistoryKey,
    WeatherStationKey,
    ensure_uppercase_icao,
)


class TestEnsureUppercaseIcao:
    """Tests for ensure_uppercase_icao function."""

    def test_valid_uppercase_icao(self):
        """Valid uppercase ICAO codes pass through."""
        assert ensure_uppercase_icao("KAUS") == "KAUS"
        assert ensure_uppercase_icao("KJFK") == "KJFK"

    def test_strips_whitespace(self):
        """Whitespace is stripped from the code."""
        assert ensure_uppercase_icao("  KAUS  ") == "KAUS"

    def test_raises_for_empty_code(self):
        """ValueError raised for empty code."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ensure_uppercase_icao("")

    def test_raises_for_whitespace_only(self):
        """ValueError raised for whitespace-only code."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ensure_uppercase_icao("   ")

    def test_raises_for_lowercase(self):
        """TypeError raised for lowercase ICAO codes."""
        with pytest.raises(TypeError, match="must be uppercase"):
            ensure_uppercase_icao("kaus")

    def test_raises_for_mixed_case(self):
        """TypeError raised for mixed case ICAO codes."""
        with pytest.raises(TypeError, match="must be uppercase"):
            ensure_uppercase_icao("Kaus")

    def test_raises_for_invalid_characters(self):
        """ValidationError raised for invalid characters."""
        with pytest.raises(ValidationError, match="invalid characters"):
            ensure_uppercase_icao("KA@US")

    def test_allows_underscores_and_dashes(self):
        """Underscores, dashes, and dots are allowed."""
        assert ensure_uppercase_icao("K_AUS") == "K_AUS"
        assert ensure_uppercase_icao("K-AUS") == "K-AUS"
        assert ensure_uppercase_icao("K.AUS") == "K.AUS"

    def test_allows_numbers(self):
        """Numbers are allowed in ICAO codes."""
        assert ensure_uppercase_icao("K123") == "K123"


class TestWeatherStationKey:
    """Tests for WeatherStationKey dataclass."""

    def test_key_generation(self):
        """Key method returns properly formatted Redis key."""
        key = WeatherStationKey(icao="KAUS")
        result = key.key()
        assert "station" in result
        assert "KAUS" in result

    def test_key_validates_icao(self):
        """Key method validates the ICAO code."""
        key = WeatherStationKey(icao="kaus")  # lowercase
        with pytest.raises(TypeError, match="must be uppercase"):
            key.key()


class TestWeatherHistoryKey:
    """Tests for WeatherHistoryKey dataclass."""

    def test_key_generation(self):
        """Key method returns properly formatted Redis key."""
        key = WeatherHistoryKey(icao="KJFK")
        result = key.key()
        assert "station_history" in result
        assert "KJFK" in result

    def test_key_validates_icao(self):
        """Key method validates the ICAO code."""
        key = WeatherHistoryKey(icao="kjfk")
        with pytest.raises(TypeError, match="must be uppercase"):
            key.key()


class TestWeatherAlertKey:
    """Tests for WeatherAlertKey dataclass."""

    def test_key_generation(self):
        """Key method returns properly formatted Redis key."""
        key = WeatherAlertKey(icao="KORD", alert_type="temperature")
        result = key.key()
        assert "station_alerts" in result
        assert "KORD" in result
        assert "temperature" in result

    def test_key_validates_icao(self):
        """Key method validates the ICAO code."""
        key = WeatherAlertKey(icao="kord", alert_type="wind")
        with pytest.raises(TypeError, match="must be uppercase"):
            key.key()

    def test_different_alert_types(self):
        """Different alert types produce different keys."""
        key1 = WeatherAlertKey(icao="KAUS", alert_type="temp")
        key2 = WeatherAlertKey(icao="KAUS", alert_type="wind")
        assert key1.key() != key2.key()
