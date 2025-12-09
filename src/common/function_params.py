"""
Common parameter dataclasses for functions with many arguments.

This module provides dataclasses to reduce function argument counts across the codebase.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


# Weather observation parameters
@dataclass
class WeatherObservationParams:
    """Parameters for weather observation storage/update operations."""

    icao_code: str
    temp_c: float
    temp_f: float
    obs_time: str
    data_source: str
    wind_direction_deg: Optional[float] = None
    wind_speed_kts: Optional[float] = None
    wind_gust_kts: Optional[float] = None
    observations: Optional[Dict[str, Any]] = None
    raw_text: Optional[str] = None


# Market update parameters
@dataclass
class MarketUpdateParams:
    """Parameters for market update operations."""

    market_key: str
    market_data: Dict[str, Any]
    ticker: str
    strike_type: str
    max_temp_f: float
    icao_code: Optional[str] = None
    weather_data: Optional[Dict[str, Any]] = None
    all_active_markets: Optional[List[Tuple[str, Dict[str, Any], str, str]]] = None


# Dependency injection parameters for service initialization
@dataclass
class ServiceDependencies:
    """Common dependency injection parameters for service initialization."""

    redis_client: Optional[Any] = None
    redis_factory: Optional[Callable] = None
    store: Optional[Any] = None
    store_factory: Optional[Callable] = None
    config: Optional[Dict[str, Any]] = None
    logger: Optional[Any] = None
    alerter: Optional[Any] = None
    alerter_factory: Optional[Callable] = None


# HTTP fetch parameters
@dataclass
class HTTPFetchParams:
    """Parameters for HTTP fetch operations."""

    base_url: str
    user_agent: str
    timeout_seconds: float
    last_modified: Optional[str] = None
    etag: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, str]] = None
