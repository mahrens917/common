"""
Metadata Extractor - Parse and extract market metadata

Handles metadata parsing, strike resolution, and price extraction.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from .metadataextractor_helpers import (
    MarketRecordBuilder,
    extract_market_prices,
    normalize_hash,
    normalize_timestamp,
    parse_market_metadata,
    resolve_market_strike,
    string_or_default,
    sync_top_of_book_fields,
)
from .metadataextractor_helpers import type_converter as _type_converter_mod


class MetadataExtractor:
    """Parse and extract market metadata from Redis hashes"""

    def __init__(self, logger_instance: logging.Logger):
        self.logger = logger_instance
        self._market_record_builder = MarketRecordBuilder(
            _type_converter_mod,
            _type_converter_mod,
            _type_converter_mod,
        )

    @staticmethod
    def string_or_default(value: Any, fill_value: str = "") -> str:
        """Convert value to string or return fill value"""
        return string_or_default(value, fill_value)

    @staticmethod
    def normalize_hash(raw_hash: Dict[Any, Any]) -> Dict[str, Any]:
        """Convert Redis hash responses to a str-keyed dictionary"""
        return normalize_hash(raw_hash)

    @staticmethod
    def sync_top_of_book_fields(snapshot: Dict[str, Any]) -> None:
        """Align scalar YES side fields with the JSON orderbook payload"""
        sync_top_of_book_fields(snapshot)

    @staticmethod
    def parse_market_metadata(market_ticker: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse metadata JSON from market data hash"""
        return parse_market_metadata(market_ticker, market_data)

    @staticmethod
    def resolve_market_strike(metadata: Dict[str, Any]) -> Optional[float]:
        """Resolve strike price from metadata fields"""
        return resolve_market_strike(metadata, string_or_default)

    @staticmethod
    def extract_market_prices(metadata: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
        """Extract best bid and ask prices from metadata"""
        return extract_market_prices(metadata)

    @staticmethod
    def normalize_timestamp(value: Any) -> Optional[str]:
        """Normalize timestamp value to string"""
        return normalize_timestamp(value)

    def create_market_record(
        self,
        market_ticker: str,
        raw_hash: Dict[str, Any],
        *,
        currency: Optional[str],
        now: datetime,
    ) -> Dict[str, Any]:
        """
        Build a market record used by currency aggregation helpers.

        Args:
            market_ticker: Market ticker
            raw_hash: Raw Redis hash
            currency: Currency symbol (optional)
            now: Current time

        Returns:
            Market record dict

        Raises:
            MarketSkip: If market should be skipped
        """
        return self._market_record_builder.create_market_record(market_ticker, raw_hash, currency=currency, now=now)
