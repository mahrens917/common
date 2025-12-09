"""
Orderbook operations delegator for KalshiStore.

Handles orderbook snapshot and delta processing.
"""

from typing import Any, Dict

from redis.asyncio import Redis

from .orderbook import KalshiOrderbookProcessor


class OrderbookDelegator:
    """Handles orderbook operations delegation."""

    def __init__(self, orderbook_processor: KalshiOrderbookProcessor) -> None:
        """Initialize orderbook delegator."""
        self._orderbook = orderbook_processor

    async def update_orderbook(self, message: Dict) -> bool:
        """Update orderbook from WebSocket message."""
        return await self._orderbook.update_orderbook(message)

    async def _process_orderbook_snapshot(
        self,
        *,
        redis: Redis,
        market_key: str,
        market_ticker: str,
        msg_data: Dict[str, Any],
        timestamp: str,
    ) -> bool:
        """Process orderbook snapshot (exposed for testing)."""
        return await self._orderbook.process_snapshot(
            redis=redis,
            market_key=market_key,
            market_ticker=market_ticker,
            msg_data=msg_data,
            timestamp=timestamp,
        )

    async def _process_orderbook_delta(
        self,
        *,
        redis: Redis,
        market_key: str,
        market_ticker: str,
        msg_data: Dict[str, Any],
        timestamp: str,
    ) -> bool:
        """Process orderbook delta (exposed for testing)."""
        return await self._orderbook.process_delta(
            redis=redis,
            market_key=market_key,
            market_ticker=market_ticker,
            msg_data=msg_data,
            timestamp=timestamp,
        )
