"""
Metadata Parser - Parse metadata JSON from market data

Handles JSON deserialization with error recovery.
"""

import logging
from typing import Any, Dict, Optional

import orjson

logger = logging.getLogger(__name__)


class MetadataParser:
    """Parse metadata JSON from market data"""

    @staticmethod
    def parse_market_metadata(market_ticker: str, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse metadata JSON from market data hash

        Args:
            market_ticker: Ticker for logging
            market_data: Market data hash

        Returns:
            Parsed metadata dict or None if invalid
        """
        metadata_blob = market_data.get("metadata") if market_data else None
        if metadata_blob is None:
            return None
        try:
            return orjson.loads(metadata_blob)
        except orjson.JSONDecodeError:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
            logger.warning("Invalid metadata JSON for market %s", market_ticker)
            return None
