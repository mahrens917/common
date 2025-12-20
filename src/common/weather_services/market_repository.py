from __future__ import annotations

"""Repositories for weather market data stored in Redis."""

import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional, Protocol

from common.config.redis_schema import get_schema_config
from common.redis_protocol import ensure_market_metadata_fields
from common.redis_protocol.converters import decode_redis_hash
from common.redis_protocol.kalshi_store import KalshiStore
from common.redis_protocol.typing import RedisClient, ensure_awaitable
from common.redis_schema import WeatherStationKey, parse_kalshi_market_key

logger = logging.getLogger(__name__)
SCHEMA = get_schema_config()


@dataclass(frozen=True)
class MarketSnapshot:
    """Minimal market view shared between tracker and updater."""

    key: str
    ticker: str
    strike_type: str
    data: Dict[str, Any]


class MarketRepository(Protocol):
    """Protocol describing the operations needed by weather services."""

    async def get_weather_data(self, station_icao: str) -> Dict[str, Any]:
        """Return the decoded weather hash for the requested station."""
        ...

    def iter_city_markets(
        self,
        city_code: str,
        *,
        day_code: Optional[str] = None,
    ) -> AsyncIterator[MarketSnapshot]:
        """Yield market snapshots for the given city (optionally filtered by day code)."""
        ...

    async def set_market_fields(self, market_key: str, mapping: Dict[str, Any]) -> None:
        """Persist hash fields for a market in Redis."""
        ...


class RedisWeatherMarketRepository(MarketRepository):
    """Redis-backed implementation that coordinates Kalshi market access."""

    def __init__(self, redis_client: RedisClient, kalshi_store: KalshiStore) -> None:
        self._redis = redis_client
        self._kalshi_store = kalshi_store

    async def get_weather_data(self, station_icao: str) -> Dict[str, Any]:
        station_key = WeatherStationKey(icao=station_icao).key()
        raw = await ensure_awaitable(self._redis.hgetall(station_key))
        return decode_redis_hash(raw)

    async def iter_city_markets(
        self,
        city_code: str,
        *,
        day_code: Optional[str] = None,
    ) -> AsyncIterator[MarketSnapshot]:
        pattern = f"{SCHEMA.kalshi_weather_prefix}:*{city_code.lower()}*"

        async for key in self._scan(pattern):
            key_str = key.decode() if isinstance(key, bytes) else str(key)

            if key_str.endswith(":trading_signal") or ":position_state" in key_str:
                continue

            try:
                descriptor = parse_kalshi_market_key(key_str)
            except (
                ValueError,
                TypeError,
            ):
                continue

            if day_code and day_code not in descriptor.ticker:
                continue

            snapshot = await self._kalshi_store.get_market_snapshot_by_key(key_str)
            if not snapshot:
                continue

            enriched_snapshot = ensure_market_metadata_fields(
                descriptor.ticker,
                snapshot,
                descriptor=descriptor,
            )

            strike_type = self._resolve_strike_type(descriptor.ticker, enriched_snapshot)

            yield MarketSnapshot(
                key=key_str,
                ticker=descriptor.ticker,
                strike_type=strike_type,
                data=enriched_snapshot,
            )

    async def set_market_fields(self, market_key: str, mapping: Dict[str, Any]) -> None:
        await ensure_awaitable(self._redis.hset(market_key, mapping=mapping))

    async def _scan(self, pattern: str, *, count: int = 500) -> AsyncIterator[Any]:
        """Asynchronously iterate over Redis keys matching a pattern."""
        cursor = 0
        while True:
            cursor, batch = await ensure_awaitable(self._redis.scan(cursor=cursor, match=pattern, count=count))
            for key in batch:
                yield key
            if cursor == 0:
                break

    @staticmethod
    def _resolve_strike_type(ticker: str, snapshot: Dict[str, Any]) -> str:
        """Determine the strike classification for a weather market snapshot."""
        strike = snapshot.get("strike_type")
        if isinstance(strike, str) and strike.strip():
            return strike.lower()

        parts = [segment.upper() for segment in ticker.split("-") if segment]
        for candidate in ("BETWEEN", "GREATER", "LESS", "ABOVE", "BELOW"):
            if candidate in parts:
                return candidate.lower()
        return "unknown"


__all__ = ["MarketRepository", "MarketSnapshot", "RedisWeatherMarketRepository"]
