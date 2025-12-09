from __future__ import annotations

"""Redis schema configuration and type-safe key builders."""


import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from .errors import ConfigurationError

CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "redis_schema.json"


@dataclass(frozen=True)
class RedisNamespaceConfig:
    name: str
    prefix: str


@dataclass(frozen=True)
class RedisSchemaConfig:
    # Deribit namespaces
    deribit_market_prefix: str
    deribit_spot_prefix: str
    deribit_gp_surface_prefix: str
    deribit_gp_metadata_key: str
    deribit_subscriptions_key: str
    deribit_instrument_lookup_key: str

    # Kalshi namespaces
    kalshi_market_prefix: str
    kalshi_weather_prefix: str
    kalshi_subscriptions_key: str
    kalshi_subscription_ids_key: str
    kalshi_trading_active_key: str
    kalshi_exchange_active_key: str

    # Weather namespaces
    weather_station_prefix: str
    weather_station_history_prefix: str
    weather_station_mapping_key: str
    weather_forecast_prefix: str
    weather_features_prefix: str
    weather_rule_4_trigger_suffix: str

    # PDF namespaces
    pdf_phase4_filters_key: str

    # Monitoring namespaces
    monitoring_status_prefix: str
    monitoring_history_prefix: str
    monitoring_monitor_jobs_prefix: str

    # CFB namespaces
    cfb_price_prefix: str

    _instance: ClassVar[RedisSchemaConfig | None] = None

    @classmethod
    def load(cls) -> "RedisSchemaConfig":
        if cls._instance is not None:
            return cls._instance

        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)

        deribit = _require_section(raw, "deribit")
        kalshi = _require_section(raw, "kalshi")
        weather = _require_section(raw, "weather")
        pdf = _require_section(raw, "pdf")
        monitoring = _require_section(raw, "monitoring")
        cfb = _require_section(raw, "cfb")

        cls._instance = cls(
            deribit_market_prefix=_require_string(deribit, "market_prefix", "deribit"),
            deribit_spot_prefix=_require_string(deribit, "spot_prefix", "deribit"),
            deribit_gp_surface_prefix=_require_string(deribit, "gp_surface_prefix", "deribit"),
            deribit_gp_metadata_key=_require_string(deribit, "gp_metadata_key", "deribit"),
            deribit_subscriptions_key=_require_string(deribit, "subscriptions_key", "deribit"),
            deribit_instrument_lookup_key=_require_string(
                deribit, "instrument_lookup_key", "deribit"
            ),
            kalshi_market_prefix=_require_string(kalshi, "market_prefix", "kalshi"),
            kalshi_weather_prefix=_require_string(kalshi, "weather_prefix", "kalshi"),
            kalshi_subscriptions_key=_require_string(kalshi, "subscriptions_key", "kalshi"),
            kalshi_subscription_ids_key=_require_string(kalshi, "subscription_ids_key", "kalshi"),
            kalshi_trading_active_key=_require_string(kalshi, "trading_active_key", "kalshi"),
            kalshi_exchange_active_key=_require_string(kalshi, "exchange_active_key", "kalshi"),
            weather_station_prefix=_require_string(weather, "station_prefix", "weather"),
            weather_station_history_prefix=_require_string(
                weather, "station_history_prefix", "weather"
            ),
            weather_station_mapping_key=_require_string(weather, "station_mapping_key", "weather"),
            weather_forecast_prefix=_require_string(weather, "forecast_prefix", "weather"),
            weather_features_prefix=_require_string(weather, "features_prefix", "weather"),
            weather_rule_4_trigger_suffix=_require_string(
                weather, "rule_4_trigger_suffix", "weather"
            ),
            pdf_phase4_filters_key=_require_string(pdf, "phase4_filters_key", "pdf"),
            monitoring_status_prefix=_require_string(monitoring, "status_prefix", "monitoring"),
            monitoring_history_prefix=_require_string(monitoring, "history_prefix", "monitoring"),
            monitoring_monitor_jobs_prefix=_require_string(
                monitoring, "monitor_jobs_prefix", "monitoring"
            ),
            cfb_price_prefix=_require_string(cfb, "price_prefix", "cfb"),
        )
        return cls._instance


def get_schema_config() -> RedisSchemaConfig:
    return RedisSchemaConfig.load()


class MarketKeys:
    """Type-safe key builders for market data."""

    @staticmethod
    def kalshi_market(category: str, ticker: str) -> str:
        """Build key for Kalshi market data."""
        schema = get_schema_config()
        return f"{schema.kalshi_market_prefix}:{category}:{ticker}"

    @staticmethod
    def kalshi_weather_market(ticker: str) -> str:
        """Build key for Kalshi weather market data."""
        schema = get_schema_config()
        return f"{schema.kalshi_weather_prefix}:{ticker}"

    @staticmethod
    def deribit_option(currency: str, expiry: str, strike: int, option_type: str) -> str:
        """Build key for Deribit option data."""
        schema = get_schema_config()
        return f"{schema.deribit_market_prefix}:option:{currency}:{expiry}:{strike}:{option_type}"

    @staticmethod
    def deribit_spot(currency: str) -> str:
        """Build key for Deribit spot price data."""
        schema = get_schema_config()
        return f"{schema.deribit_spot_prefix}:{currency}"

    @staticmethod
    def deribit_instrument_lookup() -> str:
        """Build key for Deribit instrument name to Redis key lookup hash."""
        schema = get_schema_config()
        return schema.deribit_instrument_lookup_key


class WeatherKeys:
    """Type-safe key builders for weather data."""

    @staticmethod
    def station(icao: str) -> str:
        """Build key for weather station data (includes observations and features)."""
        schema = get_schema_config()
        return f"{schema.weather_station_prefix}:{icao}"

    @staticmethod
    def station_history(icao: str) -> str:
        """Build key for weather station historical data."""
        schema = get_schema_config()
        return f"{schema.weather_station_history_prefix}:{icao}"

    @staticmethod
    def station_mapping() -> str:
        """Build key for station ICAO to friendly name mapping."""
        schema = get_schema_config()
        return schema.weather_station_mapping_key

    @staticmethod
    def forecast(station_code: str) -> str:
        """Build key for weather forecast data."""
        schema = get_schema_config()
        return f"{schema.weather_forecast_prefix}:{station_code}"

    @staticmethod
    def features(station_id: str) -> str:
        """Build key for weather features data."""
        schema = get_schema_config()
        return f"{schema.weather_features_prefix}:{station_id}"

    @staticmethod
    def rule_4_trigger(icao: str) -> str:
        """Build key pattern for rule 4 trigger flags."""
        schema = get_schema_config()
        return f"{schema.weather_station_prefix}:{icao}:{schema.weather_rule_4_trigger_suffix}"


class AnalyticsKeys:
    """Type-safe key builders for analytics and PDF data."""

    @staticmethod
    def gp_surface(currency: str) -> str:
        """Build key for GP fitted surface data."""
        schema = get_schema_config()
        return f"{schema.deribit_gp_surface_prefix}:{currency}"

    @staticmethod
    def gp_metadata() -> str:
        """Build key for GP surface metadata."""
        schema = get_schema_config()
        return schema.deribit_gp_metadata_key

    @staticmethod
    def pdf_phase4_filters() -> str:
        """Build key for PDF Phase 4 filter configuration."""
        schema = get_schema_config()
        return schema.pdf_phase4_filters_key


class ServiceStateKeys:
    """Type-safe key builders for service state and subscriptions."""

    @staticmethod
    def status(service: str) -> str:
        """Build key for service status."""
        schema = get_schema_config()
        return f"{schema.monitoring_status_prefix}:{service}"

    @staticmethod
    def kalshi_subscriptions() -> str:
        """Build key for Kalshi market subscriptions."""
        schema = get_schema_config()
        return schema.kalshi_subscriptions_key

    @staticmethod
    def kalshi_subscription_ids() -> str:
        """Build key for Kalshi WebSocket subscription IDs."""
        schema = get_schema_config()
        return schema.kalshi_subscription_ids_key

    @staticmethod
    def kalshi_trading_active() -> str:
        """Build key for Kalshi trading active flag."""
        schema = get_schema_config()
        return schema.kalshi_trading_active_key

    @staticmethod
    def kalshi_exchange_active() -> str:
        """Build key for Kalshi exchange active flag."""
        schema = get_schema_config()
        return schema.kalshi_exchange_active_key

    @staticmethod
    def deribit_subscriptions() -> str:
        """Build key for Deribit subscriptions."""
        schema = get_schema_config()
        return schema.deribit_subscriptions_key


class MonitoringKeys:
    """Type-safe key builders for monitoring and telemetry."""

    @staticmethod
    def history(source: str) -> str:
        """Build key for history/telemetry data."""
        schema = get_schema_config()
        return f"{schema.monitoring_history_prefix}:{source}"

    @staticmethod
    def monitor_job(job_name: str) -> str:
        """Build key for monitor job state."""
        schema = get_schema_config()
        return f"{schema.monitoring_monitor_jobs_prefix}:{job_name}"


class CFBKeys:
    """Type-safe key builders for CFB price data."""

    @staticmethod
    def price(currency: str) -> str:
        """Build key for CFB price data."""
        schema = get_schema_config()
        return f"{schema.cfb_price_prefix}:{currency}:price"


class TradeKeys:
    """Type-safe key builders for trade data."""

    @staticmethod
    def analysis(ticker: str) -> str:
        """Build key for trade analysis data."""
        return f"trades:analysis:{ticker}"

    @staticmethod
    def by_station(station_icao: str) -> str:
        """Build key for trades by station."""
        return f"trades:by_station:{station_icao}"


def _require_section(raw: Mapping[str, object], name: str) -> Mapping[str, object]:
    try:
        section = raw[name]
    except KeyError as exc:
        raise ConfigurationError(f"Redis schema configuration missing '{name}' section") from exc
    if not isinstance(section, Mapping):
        raise ConfigurationError(
            f"Redis schema configuration section '{name}' must be an object; received {type(section).__name__}"
        )
    return section


def _require_string(section: Mapping[str, object], key: str, section_name: str) -> str:
    try:
        value = section[key]
    except KeyError as exc:
        raise ConfigurationError(
            f"Redis schema configuration missing '{key}' in '{section_name}' section"
        ) from exc
    if not isinstance(value, str) or not value:
        raise ConfigurationError(
            f"Redis schema configuration value '{section_name}.{key}' must be a non-empty string"
        )
    return value
