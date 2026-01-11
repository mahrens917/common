"""Protocol definitions for KalshiStore dependency injection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, Tuple

from .protocols_connections import IConnectionDelegator
from .protocols_subscriptions import ISubscriptionDelegator, ISubscriptionTracker

if TYPE_CHECKING:
    from redis.asyncio import Redis


class IRedisConnectionManager(IConnectionDelegator, Protocol):
    """Protocol for Redis connection management."""

    async def get_redis(self) -> Redis:
        """Get Redis connection with health check."""
        ...

    def reset_connection_state(self) -> None:
        """Reset connection state."""
        ...

    async def close_redis_client(self, redis_client: Any) -> None:
        """Close Redis client."""
        ...

    def resolve_connection_settings(self) -> Dict[str, Any]:
        """Resolve connection settings."""
        ...

    async def acquire_pool(self, *, allow_reuse: bool) -> Redis:
        """Acquire connection pool."""
        ...

    async def create_redis_client(self) -> Redis:
        """Create Redis client."""
        ...

    async def verify_connection(self, redis: Any) -> Tuple[bool, bool]:
        """Verify connection health."""
        ...

    async def ping_connection(self, redis: Any, *, timeout: float = 5.0) -> Tuple[bool, bool]:
        """Ping connection with timeout."""
        ...

    async def ensure_redis_connection(self) -> bool:
        """Ensure Redis connection is available."""
        ...

    def ensure_ready(self) -> None:
        """Ensure store is ready for operations."""
        ...

    async def initialize(self) -> bool:
        """Initialize Redis connection."""
        ...

    async def close(self) -> None:
        """Close Redis connection."""
        ...


class IMarketReader(Protocol):
    """Protocol for market read operations."""

    def get_market_key(self, market_ticker: str) -> str:
        """Get Redis key for market ticker."""
        ...

    async def get_markets_by_currency(self, currency: str) -> List[Dict[str, Any]]:
        """Get all markets for a currency."""
        ...

    async def get_all_markets(self) -> List[Dict[str, Any]]:
        """Get all markets."""
        ...

    async def get_active_strikes_and_expiries(self, currency: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get active strikes and expiries for a currency."""
        ...

    async def get_market_data_for_strike_expiry(self, currency: str, expiry_date: str, strike: float) -> Optional[Dict[str, Any]]:
        """Get market data for specific strike and expiry."""
        ...

    async def is_market_expired(self, market_ticker: str, *, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Check if market is expired."""
        ...

    async def is_market_settled(self, market_ticker: str) -> bool:
        """Check if market is settled."""
        ...

    async def get_market_snapshot(self, ticker: str, *, include_orderbook: bool = True) -> Dict[str, Any]:
        """Get market snapshot."""
        ...

    async def get_market_snapshot_by_key(self, market_key: str, *, include_orderbook: bool = True) -> Dict[str, Any]:
        """Get market snapshot by Redis key."""
        ...

    async def get_market_metadata(self, ticker: str) -> Dict[str, Any]:
        """Get market metadata."""
        ...

    async def get_orderbook(self, ticker: str) -> Dict[str, Any]:
        """Get orderbook for market."""
        ...

    async def get_market_field(self, ticker: str, field: str, *, fallback_value: Optional[str] = None) -> Optional[str]:
        """Get single market field."""
        ...

    async def get_orderbook_side(self, ticker: str, side: str) -> Dict[str, Any]:
        """Get orderbook side (bids or asks)."""
        ...

    async def is_market_tracked(self, market_ticker: str, *, category: Optional[str] = None) -> bool:
        """Check if market is tracked."""
        ...

    def is_market_for_currency(self, market_ticker: str, currency: str) -> bool:
        """Check if market is for specific currency."""
        ...

    async def scan_market_keys(self, patterns: Optional[List[str]] = None) -> List[str]:
        """Scan for market keys matching patterns."""
        ...

    def ensure_market_metadata_fields(self, ticker: str, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required metadata fields are present."""
        ...


class IMarketWriter(Protocol):
    """Protocol for market write operations."""

    async def store_market_metadata(
        self,
        market_ticker: str,
        market_data: Dict[str, Any],
        *,
        event_data: Optional[Dict[str, Any]] = None,
        overwrite: bool = True,
    ) -> bool:
        """Store market metadata in Redis."""
        ...

    def build_kalshi_metadata(
        self,
        market_ticker: str,
        market_data: Dict[str, Any],
        event_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build Kalshi metadata from market/event data."""
        ...

    def extract_weather_station_from_ticker(self, market_ticker: str) -> Optional[str]:
        """Extract weather station from market ticker."""
        ...

    def derive_expiry_iso(self, market_ticker: str, metadata: Dict[str, Any]) -> str:
        """Derive ISO expiry date from ticker and metadata."""
        ...

    async def write_enhanced_market_data(self, ticker: str, key: str, updates: Dict[str, Any]) -> None:
        """Write enhanced market data."""
        ...

    async def update_trade_prices_for_market(self, ticker: str, bid: Optional[float], ask: Optional[float]) -> None:
        """Update trade prices for a market."""
        ...


class IMetadataDelegator(Protocol):
    """Protocol for metadata delegation operations."""

    async def store_market_metadata(
        self,
        market_ticker: str,
        market_data: Dict[str, Any],
        *,
        event_data: Optional[Dict[str, Any]] = None,
        overwrite: bool = True,
    ) -> bool:
        """Store market metadata."""
        ...

    def build_kalshi_metadata(
        self,
        market_ticker: str,
        market_data: Dict[str, Any],
        event_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build Kalshi metadata."""
        ...

    def extract_weather_station_from_ticker(self, market_ticker: str) -> Optional[str]:
        """Extract weather station from ticker."""
        ...

    def derive_expiry_iso(self, market_ticker: str, metadata: Dict[str, Any]) -> str:
        """Derive ISO expiry date."""
        ...

    def ensure_market_metadata_fields(
        self,
        market_ticker: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Ensure all required metadata fields."""
        ...


class IMarketQueryDelegator(Protocol):
    """Protocol for market query delegation operations."""

    def get_market_key(self, market_ticker: str) -> str:
        """Get Redis key for market."""
        ...

    async def get_markets_by_currency(self, currency: str) -> List[Dict[str, Any]]:
        """Get markets by currency."""
        ...

    async def get_all_markets(self) -> List[Dict[str, Any]]:
        """Get all markets."""
        ...

    async def get_active_strikes_and_expiries(self, currency: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get active strikes and expiries."""
        ...

    async def get_market_data_for_strike_expiry(self, currency: str, expiry_date: str, strike: float) -> Optional[Dict[str, Any]]:
        """Get market data for strike/expiry."""
        ...

    async def is_market_expired(self, market_ticker: str, *, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Check if market is expired."""
        ...

    async def is_market_settled(self, market_ticker: str, *, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Check if market is settled."""
        ...

    async def get_market_snapshot(self, ticker: str, *, include_orderbook: bool = True) -> Dict[str, Any]:
        """Get market snapshot."""
        ...

    async def get_market_snapshot_by_key(self, market_key: str, *, include_orderbook: bool = True) -> Dict[str, Any]:
        """Get market snapshot by key."""
        ...

    async def get_market_metadata(self, ticker: str) -> Dict[str, Any]:
        """Get market metadata."""
        ...

    async def get_orderbook(self, ticker: str) -> Dict[str, Any]:
        """Get orderbook."""
        ...

    async def get_market_field(self, ticker: str, field: str, *, fallback_value: Optional[str] = None) -> Optional[str]:
        """Get market field."""
        ...

    async def get_orderbook_side(self, ticker: str, side: str) -> Dict[str, Any]:
        """Get orderbook side."""
        ...

    async def is_market_tracked(self, market_ticker: str, *, category: Optional[str] = None) -> bool:
        """Check if market is tracked."""
        ...

    def is_market_for_currency(self, market_ticker: str, currency: str) -> bool:
        """Check if market is for currency."""
        ...

    async def scan_market_keys(self, patterns: Optional[List[str]] = None) -> List[str]:
        """Scan market keys."""
        ...


__all__ = [
    "IRedisConnectionManager",
    "IMarketReader",
    "IMarketWriter",
    "ISubscriptionTracker",
    "IConnectionDelegator",
    "IMetadataDelegator",
    "ISubscriptionDelegator",
    "IMarketQueryDelegator",
]
