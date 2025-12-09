"""Async methods mixin for KalshiMarketReader.

Provides interface declarations for async methods that are dynamically bound
at module level.
"""

from typing import Any, Dict, List, Optional, Set


class KalshiMarketReaderAsyncMethodsMixin:
    """Stub async methods that are dynamically replaced at module level."""

    async def get_subscribed_markets(self) -> Set[str]:
        """Get set of subscribed markets."""
        raise NotImplementedError

    async def is_market_tracked(self, market_ticker: str) -> bool:
        """Check if market is tracked."""
        raise NotImplementedError

    async def get_markets_by_currency(self, currency: str) -> List[Dict[str, Any]]:
        """Get markets by currency."""
        raise NotImplementedError

    async def get_active_strikes_and_expiries(
        self, currency: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get active strikes and expiries for currency."""
        raise NotImplementedError

    async def get_market_data_for_strike_expiry(
        self, currency: str, expiry: str, strike: float
    ) -> Optional[Dict[str, Any]]:
        """Get market data for strike and expiry."""
        raise NotImplementedError

    async def is_market_expired(
        self, market_ticker: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if market is expired."""
        raise NotImplementedError

    async def is_market_settled(self, market_ticker: str) -> bool:
        """Check if market is settled."""
        raise NotImplementedError

    async def get_market_snapshot(
        self, ticker: str, *, include_orderbook: bool = True
    ) -> Dict[str, Any]:
        """Get market snapshot."""
        raise NotImplementedError

    async def get_market_snapshot_by_key(
        self, market_key: str, *, include_orderbook: bool = True
    ) -> Dict[str, Any]:
        """Get market snapshot by key."""
        raise NotImplementedError

    async def get_market_metadata(self, ticker: str) -> Dict[str, Any]:
        """Get market metadata."""
        raise NotImplementedError

    async def get_market_field(self, ticker: str, field: str, default: Optional[str] = None) -> str:
        """Get specific market field."""
        raise NotImplementedError

    async def get_orderbook(self, ticker: str) -> Dict[str, Any]:
        """Get orderbook for market."""
        raise NotImplementedError

    async def get_orderbook_side(self, ticker: str, side: str) -> Dict[str, Any]:
        """Get orderbook side for market."""
        raise NotImplementedError

    async def scan_market_keys(self, patterns: Optional[List[str]] = None) -> List[str]:
        """Scan for market keys matching patterns."""
        raise NotImplementedError
