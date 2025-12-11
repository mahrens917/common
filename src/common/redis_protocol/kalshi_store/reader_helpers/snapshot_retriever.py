"""Snapshot retrieval helper for KalshiMarketReader."""

from typing import Any, Dict

from .snapshot_reader import SnapshotReader
from .snapshotreader_helpers import KalshiStoreError


class SnapshotRetriever:
    """Retrieves market snapshots and metadata."""

    def __init__(self, conn_wrapper, snapshot_reader: SnapshotReader, get_key_fn):
        self._conn = conn_wrapper
        self._snapshot_reader = snapshot_reader
        self._get_key = get_key_fn

    async def get_snapshot(self, ticker: str, *, include_orderbook: bool = True) -> Dict[str, Any]:
        """Get market snapshot."""
        try:
            redis = await self._conn.get_redis()
        except RuntimeError as exc:
            raise KalshiStoreError("Unable to acquire Redis for market snapshot") from exc
        return await self._snapshot_reader.get_market_snapshot(redis, self._get_key(ticker), ticker, include_orderbook=include_orderbook)

    async def get_snapshot_by_key(self, market_key: str, *, include_orderbook: bool = True) -> Dict[str, Any]:
        """Get market snapshot by key."""
        if not market_key:
            raise TypeError("market_key must be provided")
        from ...redis_schema.kalshi import parse_kalshi_market_key

        try:
            descriptor = parse_kalshi_market_key(market_key)
        except ValueError as exc:
            raise TypeError(str(exc)) from exc
        return await self.get_snapshot(descriptor.ticker, include_orderbook=include_orderbook)

    async def get_metadata(self, ticker: str) -> Dict:
        """Get market metadata."""
        redis = await self._conn.get_redis()
        return await self._snapshot_reader.get_market_metadata(redis, self._get_key(ticker), ticker)

    async def get_field(self, ticker: str, field: str) -> str:
        """Get specific market field."""
        if not await self._conn.ensure_connection():
            return ""
        redis = await self._conn.get_redis()
        return await self._snapshot_reader.get_market_field(redis, self._get_key(ticker), ticker, field)
