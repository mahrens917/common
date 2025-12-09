"""
Market Record Builder - Build market records from Redis data

Handles creation of market records with metadata and filtering.
"""

import logging
from collections import Counter
from typing import Any, Dict, List

from redis.asyncio import Redis

from .... import time_utils
from ...typing import ensure_awaitable
from ..market_skip import MarketSkip

logger = logging.getLogger(__name__)


async def build_market_records(
    redis: Redis,
    market_tickers: List[str],
    currency: str,
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
        currency: Currency to filter by
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

    for raw_ticker in market_tickers:
        market_ticker = ticker_parser.normalize_ticker(raw_ticker)
        try:
            market_key = get_market_key_func(market_ticker)
            raw_hash = await ensure_awaitable(redis.hgetall(market_key))
            record = metadata_extractor.create_market_record(
                market_ticker, raw_hash, currency=currency, now=current_time
            )
        except MarketSkip as skip:
            skip_reasons[skip.reason] += 1
            logger_instance.debug("Skipping market %s: %s", market_ticker, skip)
            continue

        results.append(record)

    return results, skip_reasons
