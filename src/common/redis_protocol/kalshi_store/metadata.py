from __future__ import annotations

"""
Metadata enrichment utilities for KalshiStore.

These helpers are intentionally isolated from the main store so they can be
tested independently and reused by other services that need to interpret
Kalshi market metadata.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ...redis_schema import KalshiMarketDescriptor, describe_kalshi_ticker
from ..market_metadata_builder import build_market_metadata
from ..weather_station_resolver import WeatherStationResolver
from .metadata_helpers import (
    derive_expiry_iso_impl,
    enrich_metadata_fields,
    extract_station_from_ticker,
)
from .metadata_helpers import normalize_timestamp as _normalize_timestamp
from .metadata_helpers import select_timestamp_value as _select_timestamp_value


class KalshiMetadataAdapter:
    """Encapsulates metadata derivation logic for Kalshi markets."""

    def __init__(
        self,
        *,
        logger: logging.Logger,
        weather_resolver: WeatherStationResolver,
    ) -> None:
        self._logger = logger
        self._weather_resolver = weather_resolver

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def extract_weather_station_from_ticker(self, market_ticker: str) -> Optional[str]:
        """
        Extract a 4-letter ICAO weather station code from a KXHIGH ticker.

        Returns ``None`` when the ticker does not encode weather data or when
        the resolver cannot map the alias.
        """
        return extract_station_from_ticker(market_ticker, self._weather_resolver, self._logger)

    def derive_expiry_iso(
        self,
        market_ticker: str,
        metadata: Dict[str, Any],
        descriptor_expiry_token: Optional[str],
        *,
        now_dt: Optional[datetime] = None,
    ) -> str:
        """Derive an ISO8601 expiry for a market when Kalshi REST metadata is incomplete."""
        return derive_expiry_iso_impl(market_ticker, metadata, descriptor_expiry_token, now_dt=now_dt)

    def ensure_market_metadata_fields(self, market_ticker: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Populate essential metadata fields when REST ingestion is missing."""
        return enrich_metadata_fields(market_ticker, metadata)

    def build_kalshi_metadata(
        self,
        market_ticker: str,
        market_data: Dict[str, Any],
        event_data: Optional[Dict[str, Any]] = None,
        descriptor: Optional[KalshiMarketDescriptor] = None,
        weather_resolver: Optional[WeatherStationResolver] = None,
    ) -> Dict[str, str]:
        """Build Kalshi metadata dictionary for direct Redis writes."""
        descriptor = descriptor or describe_kalshi_ticker(market_ticker)
        resolver = weather_resolver or self.weather_resolver
        return build_market_metadata(
            market_ticker=market_ticker,
            market_data=market_data,
            event_data=event_data,
            descriptor=descriptor,
            weather_resolver=resolver,
            logger=self._logger,
        )

    @property
    def weather_resolver(self) -> WeatherStationResolver:
        """Expose the underlying weather resolver for metadata builders."""
        return self._weather_resolver

    @staticmethod
    def normalize_timestamp(value: Any) -> Optional[str]:
        """Normalize a timestamp value to ISO8601 format via canonical helper."""
        return _normalize_timestamp(value)

    @staticmethod
    def select_timestamp_value(market_data: Dict[str, Any], fields: List[str]) -> Optional[object]:
        """Select the first non-empty timestamp value from a list of field names."""
        return _select_timestamp_value(market_data, fields)
