"""
Snapshot Retriever - Retrieve and parse market snapshots from Redis

Handles raw snapshot retrieval, normalization, and orderbook filtering.
"""

import logging
from typing import Any, Dict

from redis.asyncio import Redis

from ....error_types import REDIS_ERRORS
from ....typing import ensure_awaitable

logger = logging.getLogger(__name__)


class KalshiStoreError(RuntimeError):
    """Raised when KalshiStore operations cannot complete successfully."""


async def get_market_snapshot(
    redis: Redis,
    market_key: str,
    ticker: str,
    metadata_extractor,
    *,
    include_orderbook: bool = True,
) -> Dict[str, Any]:
    """
    Return the canonical Redis hash for a Kalshi market ticker.

    Args:
        redis: Redis connection
        market_key: Redis key for market
        ticker: Market ticker
        metadata_extractor: MetadataExtractor instance for normalization
        include_orderbook: Whether to include orderbook fields

    Returns:
        Market snapshot dictionary

    Raises:
        KalshiStoreError: If snapshot cannot be retrieved
    """
    if not ticker:
        raise TypeError("ticker must be provided for get_market_snapshot")

    try:
        raw_snapshot = await ensure_awaitable(redis.hgetall(market_key))
    except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
        raise KalshiStoreError(f"Redis error retrieving snapshot for {ticker}") from exc

    if not raw_snapshot:
        raise KalshiStoreError(f"Kalshi market {ticker} snapshot missing in Redis")

    snapshot = metadata_extractor.normalize_hash(raw_snapshot)
    metadata_extractor.sync_top_of_book_fields(snapshot)

    if not include_orderbook:
        for field_name in ("yes_bids", "yes_asks", "no_bids", "no_asks"):
            snapshot.pop(field_name, None)

    return snapshot
