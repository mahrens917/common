"""
Market Record Builder - Build market records from Redis data

Handles creation of market records with metadata and filtering.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Dict, List, Optional

from redis.asyncio import Redis

from .... import time_utils
from ...typing import ensure_awaitable
from ..market_skip import MarketSkip

logger = logging.getLogger(__name__)


async def build_market_records(
    redis: Redis,
    market_tickers: List[str],
    currency: Optional[str],
    ticker_parser,
    metadata_extractor,
    get_market_key_func,
    logger_instance: logging.Logger,
) -> tuple[List[Dict[str, Any]], Counter]:
    """
    Build market records from tickers

    Args:
        redis: Redis connection
        market_tickers: List of market ticker strings
        currency: Currency to filter by (optional)
        ticker_parser: TickerParser instance
        metadata_extractor: MetadataExtractor instance
        get_market_key_func: Function to get market key from ticker
        logger_instance: Logger instance

    Returns:
        Tuple of (market_records, skip_reasons_counter)
    """
    current_time = time_utils.get_current_utc()
    results: List[Dict[str, Any]] = []
    skip_reasons: Counter = Counter()

    if not market_tickers:
        return results, skip_reasons

    # Normalize tickers and build keys upfront
    normalized_tickers: List[str] = []
    market_keys: List[str] = []
    for raw_ticker in market_tickers:
        market_ticker = ticker_parser.normalize_ticker(raw_ticker)
        normalized_tickers.append(market_ticker)
        market_keys.append(get_market_key_func(market_ticker))

    # Pipeline all hgetall calls into a single Redis round trip
    pipe = redis.pipeline()
    for market_key in market_keys:
        pipe.hgetall(market_key)
    raw_hashes = await pipe.execute()

    # Process results
    for market_ticker, raw_hash in zip(normalized_tickers, raw_hashes):
        try:
            record = metadata_extractor.create_market_record(market_ticker, raw_hash, currency=currency, now=current_time)
        except MarketSkip as skip:  # Expected exception in loop, continuing iteration  # policy_guard: allow-silent-handler
            skip_reasons[skip.reason] += 1
            logger_instance.debug("Skipping market %s: %s", market_ticker, skip)
            continue

        results.append(record)

    return results, skip_reasons
