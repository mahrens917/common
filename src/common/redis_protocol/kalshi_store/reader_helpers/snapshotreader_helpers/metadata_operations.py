"""
Metadata Operations - Get enriched metadata for markets

Handles metadata field extraction and enrichment.
"""

from typing import Any, Dict

from redis.asyncio import Redis

from .snapshot_retriever import get_market_snapshot


async def get_market_metadata(
    redis: Redis,
    market_key: str,
    ticker: str,
    metadata_extractor,
    metadata_adapter,
) -> Dict[str, Any]:
    """
    Get all metadata fields for a market

    Args:
        redis: Redis connection
        market_key: Redis key for market
        ticker: Market ticker
        metadata_extractor: MetadataExtractor instance
        metadata_adapter: KalshiMetadataAdapter instance

    Returns:
        Dictionary of metadata fields
    """
    snapshot = await get_market_snapshot(
        redis, market_key, ticker, metadata_extractor, include_orderbook=False
    )
    if not snapshot:
        return {}

    enriched = metadata_adapter.ensure_market_metadata_fields(ticker, snapshot)
    for field_name in ("yes_bids", "yes_asks", "no_bids", "no_asks"):
        enriched.pop(field_name, None)
    return enriched
