"""
Optimized Redis market data store WITHOUT shared caching to eliminate race conditions
"""

import logging
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from redis.asyncio import ConnectionPool

from .optimized_market_store_helpers import (
    ExpiryConverter,
    InstanceCreator,
    InstrumentFetcher,
    MarketDataFetcher,
    RedisInitializer,
    SpotPriceFetcher,
)

# Forward references for type checking
if TYPE_CHECKING:
    from ..data_models.instrument import Instrument

logger = logging.getLogger(__name__)
_MISSING_INSTRUMENT_FIELD = object()


class OptimizedMarketStore:
    """Optimized store for market data in Redis WITHOUT shared caching"""

    def __init__(self, redis_or_pool):
        """Initialize market store. Args: redis_or_pool: Async Redis connection or async ConnectionPool"""
        self.redis: Optional[Any]
        self.redis_pool: Optional[ConnectionPool]
        self._initialized: bool
        self.atomic_ops: Optional[Any]
        self.redis, self.redis_pool, self._initialized, self.atomic_ops = RedisInitializer.initialize_from_pool_or_client(redis_or_pool)
        self.logger = logger
        self.spot_price_fetcher = SpotPriceFetcher(self.get_redis_client, self.atomic_ops)
        self.market_data_fetcher = MarketDataFetcher(self.get_redis_client)
        self.instrument_fetcher = InstrumentFetcher(self.get_redis_client)
        self._instrument_fetcher = self.instrument_fetcher
        self.expiry_converter = ExpiryConverter()

    @property
    def initialized(self) -> bool:
        """Expose initialization state for helper wiring."""
        return self._initialized

    @initialized.setter
    def initialized(self, value: bool) -> None:
        self._initialized = value

    async def get_redis_client(self) -> Any:
        """Public helper used by helpers that require Redis access."""
        return await self._get_redis()

    async def _get_redis(self) -> Any:
        """Get Redis connection, ensuring it's properly initialized"""
        if not self._initialized or self.redis is None:
            raise RuntimeError("Redis connection not initialized. Pass a Redis instance or ConnectionPool to constructor.")
        assert self.redis is not None
        return self.redis

    @classmethod
    async def create(cls):
        """Create a new OptimizedMarketStore instance with a Redis connection pool. Returns: OptimizedMarketStore instance"""
        return await InstanceCreator.create_instance(cls)

    async def get_spot_price(self, currency: str) -> Optional[float]:
        """Get spot price from Deribit market data using bid/ask mid-price. Args: currency: Currency symbol (BTC or ETH). Returns: Spot price calculated from market bid/ask mid-price or None if not found"""
        return await self.spot_price_fetcher.get_spot_price(currency)

    async def get_usdc_bid_ask_prices(self, currency: str) -> Tuple[float, float]:
        """Return bid/ask prices for the currency's USDC spot pair."""
        # Allow tests to inject atomic_ops after construction.
        self.spot_price_fetcher.atomic_ops = self.atomic_ops
        return await self.spot_price_fetcher.get_usdc_bid_ask_prices(currency)

    async def get_market_data(self, instrument: "Instrument", original_key: Optional[str] = None) -> dict:
        """Fetch market data for an instrument without caching. Raises: ValueError: When the key cannot be derived or the payload is incomplete."""
        return await self.market_data_fetcher.get_market_data(instrument, original_key)

    async def get_all_instruments(self, currency: str) -> List:
        """Return instruments for a currency using the unified Redis schema."""
        fetcher = getattr(self, "instrument_fetcher", None) or getattr(self, "_instrument_fetcher", None)
        if fetcher is None:
            log = getattr(self, "logger", logger)
            log.error("No instrument fetcher available for currency %s", currency)
            _none_guard_value = []
            return _none_guard_value
        try:
            return await fetcher.get_all_instruments(currency)
        except (RuntimeError, ValueError, AttributeError, KeyError, OSError, ConnectionError) as exc:  # policy_guard: allow-silent-handler
            log = getattr(self, "logger", logger)
            log.error("Failed to fetch instruments for %s: %s", currency, exc, exc_info=True)
            return []

    async def get_options_by_currency(self, currency: str) -> List:
        return await _filter_instruments(self, currency, _is_option_instrument, "options")

    async def get_futures_by_currency(self, currency: str) -> List:
        return await _filter_instruments(self, currency, _is_future_instrument, "futures")

    async def get_puts_by_currency(self, currency: str) -> List:
        return await _filter_instruments(self, currency, _is_put_instrument, "puts")

    def _convert_expiry_to_iso(self, expiry_str: str) -> str:
        return self.expiry_converter.convert_expiry_to_iso(expiry_str)

    def _convert_iso_to_deribit(self, iso_str: str) -> str:
        return self.expiry_converter.convert_iso_to_deribit(iso_str)

    async def close(self):
        """Close Redis connections"""
        if self.redis:
            await self.redis.aclose()


def _is_option_instrument(inst: Any) -> bool:
    return getattr(inst, "is_future", None) is not True


def _is_future_instrument(inst: Any) -> bool:
    return getattr(inst, "is_future", None) is True


def _is_put_instrument(inst: Any) -> bool:
    option_type = getattr(inst, "option_type", _MISSING_INSTRUMENT_FIELD)
    if option_type is _MISSING_INSTRUMENT_FIELD:
        return False
    if not isinstance(option_type, str):
        return False
    return _is_option_instrument(inst) and option_type.lower() == "put"


async def _filter_instruments(store: OptimizedMarketStore, currency: str, predicate, label: str) -> List:
    try:
        instruments = await store.get_all_instruments(currency)
        return [inst for inst in instruments if predicate(inst)]
    except (RuntimeError, ValueError, AttributeError) as exc:  # policy_guard: allow-silent-handler
        log = getattr(store, "logger", logger)
        log.error("Failed to load %s for %s: %s", label, currency, exc, exc_info=True)
        return []
