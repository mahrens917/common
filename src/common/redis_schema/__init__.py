"""Typed Redis schema helpers for the Kalshi stack."""

from common.config.redis_schema import RedisSchemaConfig, get_schema_config

from .analytics import PdfSurfaceKey, ProbabilitySliceKey, SurfaceType
from .deribit import parse_deribit_market_key
from .kalshi import (
    KalshiMarketDescriptor,
    build_kalshi_market_key,
    describe_kalshi_ticker,
    is_supported_kalshi_ticker,
    parse_kalshi_market_key,
)
from .markets import (
    DeribitInstrumentDescriptor,
    DeribitInstrumentKey,
    DeribitInstrumentType,
    KalshiMarketCategory,
    KalshiMarketKey,
    ReferenceMarketKey,
)
from .namespaces import RedisNamespace, sanitize_segment
from .operations import (
    MetricStreamKey,
    ServiceStatusKey,
    SubscriptionKey,
    SubscriptionType,
)
from .trades import TradeIndexKey, TradeRecordKey, TradeSummaryKey
from .validators import register_namespace, validate_registered_key
from .weather import (
    WeatherAlertKey,
    WeatherDailyHighKey,
    WeatherDailyLowKey,
    WeatherHistoryKey,
    WeatherStationKey,
    ensure_uppercase_icao,
)

__all__ = [
    "RedisNamespace",
    "sanitize_segment",
    "register_namespace",
    "validate_registered_key",
    "DeribitInstrumentDescriptor",
    "DeribitInstrumentKey",
    "DeribitInstrumentType",
    "KalshiMarketCategory",
    "KalshiMarketKey",
    "ReferenceMarketKey",
    "parse_deribit_market_key",
    "parse_kalshi_market_key",
    "describe_kalshi_ticker",
    "KalshiMarketDescriptor",
    "build_kalshi_market_key",
    "is_supported_kalshi_ticker",
    "PdfSurfaceKey",
    "ProbabilitySliceKey",
    "SurfaceType",
    "WeatherStationKey",
    "WeatherHistoryKey",
    "WeatherAlertKey",
    "WeatherDailyHighKey",
    "WeatherDailyLowKey",
    "ensure_uppercase_icao",
    "TradeRecordKey",
    "TradeIndexKey",
    "TradeSummaryKey",
    "SubscriptionKey",
    "SubscriptionType",
    "ServiceStatusKey",
    "MetricStreamKey",
    "RedisSchemaConfig",
    "get_schema_config",
]
