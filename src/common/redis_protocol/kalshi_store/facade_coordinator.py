"""
Coordinator for KalshiStore facade delegation.

This module consolidates all delegation logic from KalshiStore to its underlying components,
reducing the size of the main facade class.
"""

from typing import Any, Callable, Dict, List, Optional, Sequence, Set, cast

from redis.asyncio import Redis

from ...redis_schema import describe_kalshi_ticker
from .connection import RedisConnectionManager
from .facade_helpers_weather import resolve_weather_station_from_ticker
from .reader import KalshiMarketReader
from .subscription import KalshiSubscriptionTracker
from .subscription_helpers import KeyProvider
from .writer import KalshiMarketWriter


class ConnectionDelegator:
    """Handles connection management delegation."""

    def __init__(self, connection_manager: RedisConnectionManager) -> None:
        self._connection = connection_manager

    async def get_redis(self) -> Redis:
        """Get Redis connection with health check."""
        return await self._connection.get_redis()

    def reset_connection_state(self) -> None:
        """Reset connection state."""
        self._connection.reset_connection_state()

    async def close_redis_client(self, redis_client: Any) -> None:
        """Close Redis client."""
        await self._connection.close_redis_client(redis_client)

    def resolve_connection_settings(self) -> Dict[str, Any]:
        """Resolve connection settings."""
        return self._connection.resolve_connection_settings()

    async def acquire_pool(self, *, allow_reuse: bool) -> Redis:
        """Acquire connection pool."""
        return await self._connection.acquire_pool(allow_reuse=allow_reuse)

    async def create_redis_client(self) -> Redis:
        """Create Redis client."""
        return await self._connection.create_redis_client()

    async def verify_connection(self, redis: Any) -> tuple[bool, bool]:
        """Verify connection health."""
        return await self._connection.verify_connection(redis)

    async def ping_connection(self, redis: Any, *, timeout: float = 5.0) -> tuple[bool, bool]:
        """Ping connection with timeout."""
        return await self._connection.ping_connection(redis, timeout=timeout)

    async def connect_with_retry(
        self,
        *,
        allow_reuse: bool = True,
        context: str = "facade_connection",
        attempts: int = 3,
        retry_delay: float = 0.1,
    ) -> bool:
        """Connect with retry logic."""
        return await self._connection.connect_with_retry(
            allow_reuse=allow_reuse,
            context=context,
            attempts=attempts,
            retry_delay=retry_delay,
        )

    async def ensure_redis_connection(self) -> bool:
        """Ensure Redis connection is available."""
        return await self._connection.ensure_redis_connection()

    async def attach_redis_client(
        self,
        redis_client: Redis,
        *,
        health_check_timeout: float = 5.0,
    ) -> None:
        """Attach external Redis client."""
        await self._connection.attach_redis_client(
            redis_client,
            health_check_timeout=health_check_timeout,
        )

    def ensure_ready(self) -> None:
        """Ensure store is ready for operations."""
        self._connection.ensure_ready()

    async def initialize(self) -> bool:
        """Initialize Redis connection."""
        return await self._connection.initialize()

    async def close(self) -> None:  # pragma: no cover - event loop shutdown guard
        """Close Redis connection."""
        await self._connection.close()


class MetadataDelegator:
    """Handles metadata operations delegation."""

    def __init__(
        self,
        writer: KalshiMarketWriter,
        reader: KalshiMarketReader,
        weather_resolver_getter: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._writer = writer
        self._reader = reader
        self._weather_resolver_getter = weather_resolver_getter

    async def store_market_metadata(
        self,
        market_ticker: str,
        market_data: Dict[str, Any],
        *,
        event_data: Optional[Dict[str, Any]] = None,
        overwrite: bool = True,
    ) -> bool:
        """Store market metadata in Redis."""
        return await self._writer.store_market_metadata(
            market_ticker,
            market_data,
            event_data=event_data,
            overwrite=overwrite,
        )

    def build_kalshi_metadata(
        self,
        market_ticker: str,
        market_data: Dict[str, Any],
        event_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build Kalshi metadata from market/event data."""
        descriptor = describe_kalshi_ticker(market_ticker)

        metadata_writer = getattr(self._writer, "_metadata_writer", None)
        if metadata_writer is None:
            raise RuntimeError("Metadata writer is not initialized")

        weather_resolver = self._resolve_weather_resolver()

        return metadata_writer._build_kalshi_metadata(
            market_ticker, market_data, event_data, descriptor, weather_resolver
        )

    def _resolve_weather_resolver(self) -> Optional[Any]:
        if self._weather_resolver_getter:
            return self._weather_resolver_getter()
        metadata_adapter = getattr(self._writer, "_metadata", None)
        return getattr(metadata_adapter, "weather_resolver", None)

    def extract_weather_station_from_ticker(self, market_ticker: str) -> Optional[str]:
        """Extract weather station from market ticker."""
        return resolve_weather_station_from_ticker(
            market_ticker,
            writer=self._writer,
            weather_resolver=self._resolve_weather_resolver(),
        )

    def derive_expiry_iso(self, market_ticker: str, metadata: Dict[str, Any]) -> str:
        """Derive ISO expiry date from ticker and metadata."""
        descriptor = describe_kalshi_ticker(market_ticker)
        return self._writer.derive_expiry_iso(market_ticker, metadata, descriptor)

    def ensure_market_metadata_fields(
        self,
        market_ticker: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Ensure all required metadata fields are present."""
        return self._reader.ensure_market_metadata_fields(market_ticker, metadata)


class SubscriptionDelegator:
    def __init__(self, subscription_tracker: KalshiSubscriptionTracker) -> None:
        self._subscription = subscription_tracker

    @property
    def SUBSCRIPTIONS_KEY(self) -> str:
        subscriptions_key = self._subscription.SUBSCRIPTIONS_KEY
        if subscriptions_key is None:
            raise RuntimeError(
                "KalshiSubscriptionTracker has not initialized SUBSCRIPTIONS_KEY yet"
            )
        return subscriptions_key

    @property
    def SERVICE_STATUS_KEY(self) -> str:
        key_provider = cast(
            Optional[KeyProvider], getattr(self._subscription, "_key_provider", None)
        )
        if key_provider is None:
            return "status"
        return key_provider.service_status_key

    @property
    def SUBSCRIBED_MARKETS_KEY(self) -> str:
        key_provider = cast(
            Optional[KeyProvider], getattr(self._subscription, "_key_provider", None)
        )
        if key_provider is None:
            return "kalshi:subscribed_markets"
        return key_provider.subscribed_markets_key

    @property
    def SUBSCRIPTION_IDS_KEY(self) -> str:
        key_provider = cast(
            Optional[KeyProvider], getattr(self._subscription, "_key_provider", None)
        )
        if key_provider is None:
            prefix = getattr(self._subscription, "service_prefix", "ws") or "ws"
            return f"kalshi:subscription_ids:{prefix}"
        return key_provider.subscription_ids_key

    async def get_subscribed_markets(self) -> Set[str]:  # pragma: no cover
        return await self._subscription.get_subscribed_markets()

    async def add_subscribed_market(
        self, market_ticker: str, *, category: Optional[str] = None
    ) -> bool:
        return await self._subscription.add_subscribed_market(market_ticker, category=category)

    async def remove_subscribed_market(
        self,
        market_ticker: str,
        *,
        category: Optional[str] = None,
    ) -> bool:
        return await self._subscription.remove_subscribed_market(
            market_ticker,
            category=category,
        )

    async def record_subscription_ids(
        self,
        subscription_ids: Dict[str, Any] | Sequence[Any],
        market_tickers: Optional[Sequence[str]] = None,
    ) -> None:
        await self._subscription.record_subscription_ids(
            subscription_ids,
            market_tickers,
        )

    async def fetch_subscription_ids(
        self,
        *,
        market_tickers: Optional[Sequence[str]] = None,
    ) -> Dict[str, str]:
        return await self._subscription.fetch_subscription_ids(
            market_tickers=market_tickers,
        )

    async def clear_subscription_ids(
        self,
        *,
        market_tickers: Optional[Sequence[str]] = None,
    ) -> None:
        await self._subscription.clear_subscription_ids(
            market_tickers=market_tickers,
        )

    async def update_service_status(self, service: str, status: Dict) -> bool:
        return await self._subscription.update_service_status(service, status)

    async def get_service_status(self, service: str) -> Optional[str]:
        return await self._subscription.get_service_status(service)


class MarketQueryDelegator:
    """Handles market data queries delegation."""

    def __init__(self, reader: KalshiMarketReader) -> None:
        self._reader = reader

    def get_market_key(self, market_ticker: str) -> str:
        """Get Redis key for market ticker."""
        return self._reader.get_market_key(market_ticker)

    async def get_markets_by_currency(self, currency: str) -> List[Dict]:
        """Get all markets for a currency."""
        return await self._reader.get_markets_by_currency(currency)

    async def get_active_strikes_and_expiries(self, currency: str) -> Dict[str, List[Dict]]:
        """Get active strikes and expiries for a currency."""
        return await self._reader.get_active_strikes_and_expiries(currency)

    async def get_market_data_for_strike_expiry(
        self, currency: str, expiry_date: str, strike: float
    ) -> Optional[Dict]:
        """Get market data for specific strike and expiry."""
        return await self._reader.get_market_data_for_strike_expiry(currency, expiry_date, strike)

    async def is_market_expired(
        self, market_ticker: str, *, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if market is expired."""
        return await self._reader.is_market_expired(market_ticker, metadata=metadata)

    async def is_market_settled(
        self, market_ticker: str, *, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if market is settled."""
        _ = metadata
        return await self._reader.is_market_settled(market_ticker)

    async def get_market_snapshot(self, ticker: str, *, include_orderbook: bool = True) -> Dict:
        """Get market snapshot."""
        return await self._reader.get_market_snapshot(ticker, include_orderbook=include_orderbook)

    async def get_market_snapshot_by_key(
        self, market_key: str, *, include_orderbook: bool = True
    ) -> Dict:
        """Get market snapshot by Redis key."""
        return await self._reader.get_market_snapshot_by_key(
            market_key, include_orderbook=include_orderbook
        )

    async def get_market_metadata(self, ticker: str) -> Dict:
        """Get market metadata."""
        return await self._reader.get_market_metadata(ticker)

    async def get_orderbook(self, ticker: str) -> Dict:  # pragma: no cover - Redis lookup helper
        """Get orderbook for market."""
        return await self._reader.get_orderbook(ticker)

    async def get_market_field(
        self, ticker: str, field: str, *, default: Optional[str] = None
    ) -> Optional[str]:
        """Get single market field."""
        return await self._reader.get_market_field(ticker, field, default=default)

    async def get_orderbook_side(self, ticker: str, side: str) -> Dict:
        """Get orderbook side (bids or asks)."""
        return await self._reader.get_orderbook_side(ticker, side)

    async def is_market_tracked(
        self, market_ticker: str, *, category: Optional[str] = None
    ) -> bool:
        """Check if market is tracked."""
        _ = category  # category filtering handled upstream; reader tracks by ticker only
        return await self._reader.is_market_tracked(market_ticker)

    def is_market_for_currency(self, market_ticker: str, currency: str) -> bool:
        """Check if market is for specific currency."""
        return self._reader.is_market_for_currency(market_ticker, currency)

    async def scan_market_keys(self, patterns: Optional[List[str]] = None) -> List[str]:
        """Scan for market keys matching patterns."""
        return await self._reader.scan_market_keys(patterns)
