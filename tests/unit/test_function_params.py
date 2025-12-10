"""Tests for common function_params module."""

from __future__ import annotations

from typing import Any

import pytest

from common.function_params import (
    HTTPFetchParams,
    MarketUpdateParams,
    ServiceDependencies,
    WeatherObservationParams,
)


class TestWeatherObservationParams:
    """Tests for WeatherObservationParams dataclass."""

    def test_creates_with_required_fields(self) -> None:
        """Can create instance with required fields only."""
        params = WeatherObservationParams(
            icao_code="KJFK",
            temp_c=20.0,
            temp_f=68.0,
            obs_time="2024-01-01T12:00:00Z",
            data_source="NWS",
        )
        assert params.icao_code == "KJFK"
        assert params.temp_c == 20.0
        assert params.temp_f == 68.0
        assert params.obs_time == "2024-01-01T12:00:00Z"
        assert params.data_source == "NWS"

    def test_optional_fields_default_to_none(self) -> None:
        """Optional fields default to None."""
        params = WeatherObservationParams(
            icao_code="KJFK",
            temp_c=20.0,
            temp_f=68.0,
            obs_time="2024-01-01T12:00:00Z",
            data_source="NWS",
        )
        assert params.wind_direction_deg is None
        assert params.wind_speed_kts is None
        assert params.wind_gust_kts is None
        assert params.observations is None
        assert params.raw_text is None

    def test_creates_with_all_fields(self) -> None:
        """Can create instance with all fields."""
        params = WeatherObservationParams(
            icao_code="KJFK",
            temp_c=20.0,
            temp_f=68.0,
            obs_time="2024-01-01T12:00:00Z",
            data_source="NWS",
            wind_direction_deg=180.0,
            wind_speed_kts=10.0,
            wind_gust_kts=15.0,
            observations={"key": "value"},
            raw_text="METAR KJFK ...",
        )
        assert params.wind_direction_deg == 180.0
        assert params.wind_speed_kts == 10.0
        assert params.wind_gust_kts == 15.0
        assert params.observations == {"key": "value"}
        assert params.raw_text == "METAR KJFK ..."


class TestMarketUpdateParams:
    """Tests for MarketUpdateParams dataclass."""

    def test_creates_with_required_fields(self) -> None:
        """Can create instance with required fields only."""
        params = MarketUpdateParams(
            market_key="markets:kalshi:temperature:KXHIGH",
            market_data={"ticker": "KXHIGH"},
            ticker="KXHIGH",
            strike_type="high",
            max_temp_f=90.0,
        )
        assert params.market_key == "markets:kalshi:temperature:KXHIGH"
        assert params.market_data == {"ticker": "KXHIGH"}
        assert params.ticker == "KXHIGH"
        assert params.strike_type == "high"
        assert params.max_temp_f == 90.0

    def test_optional_fields_default_to_none(self) -> None:
        """Optional fields default to None."""
        params = MarketUpdateParams(
            market_key="key",
            market_data={},
            ticker="ticker",
            strike_type="type",
            max_temp_f=0.0,
        )
        assert params.icao_code is None
        assert params.weather_data is None
        assert params.all_active_markets is None


class TestServiceDependencies:
    """Tests for ServiceDependencies dataclass."""

    def test_creates_with_no_fields(self) -> None:
        """Can create instance with no fields (all optional)."""
        deps = ServiceDependencies()
        assert deps.redis_client is None
        assert deps.redis_factory is None
        assert deps.store is None
        assert deps.store_factory is None
        assert deps.config is None
        assert deps.logger is None
        assert deps.alerter is None
        assert deps.alerter_factory is None

    def test_creates_with_some_fields(self) -> None:
        """Can create instance with some fields."""
        mock_config = {"key": "value"}
        deps = ServiceDependencies(config=mock_config)
        assert deps.config == mock_config

    def test_factory_fields_accept_callables(self) -> None:
        """Factory fields accept callable objects."""

        def factory() -> Any:
            return "result"

        deps = ServiceDependencies(redis_factory=factory, store_factory=factory)
        assert callable(deps.redis_factory)
        assert callable(deps.store_factory)


class TestHTTPFetchParams:
    """Tests for HTTPFetchParams dataclass."""

    def test_creates_with_required_fields(self) -> None:
        """Can create instance with required fields only."""
        params = HTTPFetchParams(
            base_url="https://api.example.com",
            user_agent="TestClient/1.0",
            timeout_seconds=30.0,
        )
        assert params.base_url == "https://api.example.com"
        assert params.user_agent == "TestClient/1.0"
        assert params.timeout_seconds == 30.0

    def test_optional_fields_default_to_none(self) -> None:
        """Optional fields default to None."""
        params = HTTPFetchParams(
            base_url="https://api.example.com",
            user_agent="TestClient/1.0",
            timeout_seconds=30.0,
        )
        assert params.last_modified is None
        assert params.etag is None
        assert params.headers is None
        assert params.params is None

    def test_creates_with_all_fields(self) -> None:
        """Can create instance with all fields."""
        params = HTTPFetchParams(
            base_url="https://api.example.com",
            user_agent="TestClient/1.0",
            timeout_seconds=30.0,
            last_modified="Wed, 01 Jan 2024 00:00:00 GMT",
            etag='"abc123"',
            headers={"Accept": "application/json"},
            params={"page": "1"},
        )
        assert params.last_modified == "Wed, 01 Jan 2024 00:00:00 GMT"
        assert params.etag == '"abc123"'
        assert params.headers == {"Accept": "application/json"}
        assert params.params == {"page": "1"}
