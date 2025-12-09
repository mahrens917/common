"""
Tests for src/common/config/redis_schema.py

Tests type-safe Redis key builders and schema configuration loading.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.common.config.errors import ConfigurationError
from src.common.config.redis_schema import (
    AnalyticsKeys,
    CFBKeys,
    MarketKeys,
    MonitoringKeys,
    RedisSchemaConfig,
    ServiceStateKeys,
    WeatherKeys,
    _require_section,
    _require_string,
    get_schema_config,
)


class TestRedisSchemaConfig:
    """Tests for RedisSchemaConfig singleton."""

    def test_load_creates_instance(self, monkeypatch):
        """RedisSchemaConfig.load() creates and caches instance."""
        RedisSchemaConfig._instance = None
        config = RedisSchemaConfig.load()
        assert isinstance(config, RedisSchemaConfig)
        assert RedisSchemaConfig._instance is config

    def test_load_returns_cached_instance(self):
        """Subsequent calls to load() return the same instance."""
        config1 = RedisSchemaConfig.load()
        config2 = RedisSchemaConfig.load()
        assert config1 is config2

    def test_get_schema_config_delegates_to_load(self):
        """get_schema_config() returns the loaded config."""
        config = get_schema_config()
        assert isinstance(config, RedisSchemaConfig)
        assert config is RedisSchemaConfig.load()


class TestMarketKeys:
    """Tests for MarketKeys type-safe key builders."""

    def test_kalshi_market_builds_correct_key(self):
        """kalshi_market() builds key with category and ticker."""
        key = MarketKeys.kalshi_market("btc", "BTCHIGH-25JAN01")
        assert "btc" in key
        assert "BTCHIGH-25JAN01" in key
        assert key.count(":") >= 2

    def test_kalshi_weather_market_builds_correct_key(self):
        """kalshi_weather_market() builds key with ticker."""
        key = MarketKeys.kalshi_weather_market("KXHIGH-25JAN01")
        assert "KXHIGH-25JAN01" in key

    def test_deribit_option_builds_correct_key(self):
        """deribit_option() builds key with all option parameters."""
        key = MarketKeys.deribit_option("BTC", "2025-01-31", 50000, "call")
        assert "BTC" in key
        assert "2025-01-31" in key
        assert "50000" in key
        assert "call" in key
        assert key.count(":") >= 4

    def test_deribit_spot_builds_correct_key(self):
        """deribit_spot() builds key with currency."""
        key = MarketKeys.deribit_spot("BTC")
        assert "BTC" in key

    def test_deribit_instrument_lookup_returns_key(self):
        """deribit_instrument_lookup() returns the lookup key."""
        key = MarketKeys.deribit_instrument_lookup()
        assert isinstance(key, str)
        assert len(key) > 0


class TestWeatherKeys:
    """Tests for WeatherKeys type-safe key builders."""

    def test_station_builds_correct_key(self):
        """station() builds key with ICAO code."""
        key = WeatherKeys.station("KJFK")
        assert "KJFK" in key

    def test_station_history_builds_correct_key(self):
        """station_history() builds key with ICAO code."""
        key = WeatherKeys.station_history("KLAX")
        assert "KLAX" in key

    def test_station_mapping_returns_key(self):
        """station_mapping() returns the mapping key."""
        key = WeatherKeys.station_mapping()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_forecast_builds_correct_key(self):
        """forecast() builds key with station code."""
        key = WeatherKeys.forecast("KSFO")
        assert "KSFO" in key

    def test_features_builds_correct_key(self):
        """features() builds key with station ID."""
        key = WeatherKeys.features("station123")
        assert "station123" in key

    def test_rule_4_trigger_builds_correct_key(self):
        """rule_4_trigger() builds key with ICAO and trigger suffix."""
        key = WeatherKeys.rule_4_trigger("KDFW")
        assert "KDFW" in key
        assert key.count(":") >= 2


class TestAnalyticsKeys:
    """Tests for AnalyticsKeys type-safe key builders."""

    def test_gp_surface_builds_correct_key(self):
        """gp_surface() builds key with currency."""
        key = AnalyticsKeys.gp_surface("BTC")
        assert "BTC" in key

    def test_gp_metadata_returns_key(self):
        """gp_metadata() returns the metadata key."""
        key = AnalyticsKeys.gp_metadata()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_pdf_phase4_filters_returns_key(self):
        """pdf_phase4_filters() returns the filters key."""
        key = AnalyticsKeys.pdf_phase4_filters()
        assert isinstance(key, str)
        assert len(key) > 0


class TestServiceStateKeys:
    """Tests for ServiceStateKeys type-safe key builders."""

    def test_status_builds_correct_key(self):
        """status() builds key with service name."""
        key = ServiceStateKeys.status("kalshi")
        assert "kalshi" in key

    def test_kalshi_subscriptions_returns_key(self):
        """kalshi_subscriptions() returns the subscriptions key."""
        key = ServiceStateKeys.kalshi_subscriptions()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_kalshi_subscription_ids_returns_key(self):
        """kalshi_subscription_ids() returns the subscription IDs key."""
        key = ServiceStateKeys.kalshi_subscription_ids()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_kalshi_trading_active_returns_key(self):
        """kalshi_trading_active() returns the trading active key."""
        key = ServiceStateKeys.kalshi_trading_active()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_kalshi_exchange_active_returns_key(self):
        """kalshi_exchange_active() returns the exchange active key."""
        key = ServiceStateKeys.kalshi_exchange_active()
        assert isinstance(key, str)
        assert len(key) > 0

    def test_deribit_subscriptions_returns_key(self):
        """deribit_subscriptions() returns the subscriptions key."""
        key = ServiceStateKeys.deribit_subscriptions()
        assert isinstance(key, str)
        assert len(key) > 0


class TestMonitoringKeys:
    """Tests for MonitoringKeys type-safe key builders."""

    def test_history_builds_correct_key(self):
        """history() builds key with source name."""
        key = MonitoringKeys.history("trades")
        assert "trades" in key

    def test_monitor_job_builds_correct_key(self):
        """monitor_job() builds key with job name."""
        key = MonitoringKeys.monitor_job("health_check")
        assert "health_check" in key


class TestCFBKeys:
    """Tests for CFBKeys type-safe key builders."""

    def test_price_builds_correct_key(self):
        """price() builds key with currency."""
        key = CFBKeys.price("BTC")
        assert "BTC" in key
        assert "price" in key


class TestRequireSection:
    """Tests for _require_section helper function."""

    def test_returns_section_when_present(self):
        """_require_section returns section when present."""
        raw = {"deribit": {"market_prefix": "markets:deribit"}}
        section = _require_section(raw, "deribit")
        assert section == {"market_prefix": "markets:deribit"}

    def test_raises_when_section_missing(self):
        """_require_section raises ConfigurationError when section missing."""
        raw = {"kalshi": {}}
        with pytest.raises(ConfigurationError, match="missing 'deribit' section"):
            _require_section(raw, "deribit")

    def test_raises_when_section_not_mapping(self):
        """_require_section raises when section is not a mapping."""
        raw = {"deribit": "not_a_mapping"}
        with pytest.raises(ConfigurationError, match="must be an object"):
            _require_section(raw, "deribit")


class TestRequireString:
    """Tests for _require_string helper function."""

    def test_returns_string_when_present(self):
        """_require_string returns string value when present."""
        section = {"market_prefix": "markets:deribit"}
        value = _require_string(section, "market_prefix", "deribit")
        assert value == "markets:deribit"

    def test_raises_when_key_missing(self):
        """_require_string raises ConfigurationError when key missing."""
        section = {"other_key": "value"}
        with pytest.raises(ConfigurationError, match="missing 'market_prefix'"):
            _require_string(section, "market_prefix", "deribit")

    def test_raises_when_value_not_string(self):
        """_require_string raises when value is not a string."""
        section = {"market_prefix": 123}
        with pytest.raises(ConfigurationError, match="must be a non-empty string"):
            _require_string(section, "market_prefix", "deribit")

    def test_raises_when_value_empty_string(self):
        """_require_string raises when value is an empty string."""
        section = {"market_prefix": ""}
        with pytest.raises(ConfigurationError, match="must be a non-empty string"):
            _require_string(section, "market_prefix", "deribit")


class TestConfigurationErrorHandling:
    """Tests for error handling in configuration loading."""

    def test_load_raises_on_missing_required_section(self, monkeypatch, tmp_path):
        """load() raises ConfigurationError when required section missing."""
        RedisSchemaConfig._instance = None
        config_file = tmp_path / "redis_schema.json"
        config_file.write_text(
            json.dumps(
                {
                    "deribit": {"market_prefix": "markets:deribit"},
                    # Missing other sections
                }
            )
        )

        monkeypatch.setattr("src.common.config.redis_schema.CONFIG_PATH", config_file)

        with pytest.raises(ConfigurationError):
            RedisSchemaConfig.load()

    def test_load_raises_on_missing_required_field(self, monkeypatch, tmp_path):
        """load() raises ConfigurationError when required field missing."""
        RedisSchemaConfig._instance = None
        config_file = tmp_path / "redis_schema.json"
        config_file.write_text(
            json.dumps(
                {
                    "deribit": {},  # Missing required fields
                    "kalshi": {},
                    "weather": {},
                    "pdf": {},
                    "monitoring": {},
                    "cfb": {},
                }
            )
        )

        monkeypatch.setattr("src.common.config.redis_schema.CONFIG_PATH", config_file)

        with pytest.raises(ConfigurationError):
            RedisSchemaConfig.load()
