from __future__ import annotations

"""Liquidity state fetcher for visualization."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from common.config.redis_schema import get_schema_config
from common.redis_protocol.typing import RedisClient, ensure_awaitable
from common.redis_schema import parse_kalshi_market_key
from common.redis_utils import get_redis_connection

logger = logging.getLogger(__name__)


class MarketState:
    """Represents market liquidity state."""

    def __init__(
        self,
        timestamp: datetime,
        market_ticker: str,
        yes_bid: Optional[float],
        yes_ask: Optional[float],
        traded: bool,
        min_strike_price_cents: Optional[float],
        max_strike_price_cents: Optional[float],
    ) -> None:
        self.timestamp = timestamp
        self.market_ticker = market_ticker
        self.yes_bid = yes_bid
        self.yes_ask = yes_ask
        self.traded = traded
        self.min_strike_price_cents = min_strike_price_cents
        self.max_strike_price_cents = max_strike_price_cents


class LiquidityFetcher:
    """Fetch market liquidity states from Redis."""

    @staticmethod
    def safe_float(value: Optional[str]) -> Optional[float]:
        """Safely convert value to float. Delegates to canonical implementation."""
        from common.parsing_utils import safe_float_parse

        try:
            return safe_float_parse(value)
        except (ValueError, TypeError):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            logger.warning("Expected data validation or parsing failure")
            return None

    async def get_market_liquidity_states(
        self,
        station_icao: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[MarketState]:
        """Fetch market liquidity states for a station."""
        if not self._should_scan_station(station_icao):
            return []

        try:
            redis: RedisClient = await get_redis_connection()
            market_keys = await self._fetch_market_keys(redis, station_icao)
            states = await self._collect_states(redis, market_keys)
            await redis.aclose()
        except asyncio.CancelledError:
            raise
        except (
            OSError,
            ConnectionError,
            RuntimeError,
            ValueError,
        ):  # Transient network/connection failure  # policy_guard: allow-silent-handler
            logger.exception("Failed to fetch market liquidity states for %s", station_icao)
            return []
        else:
            return states

    def _should_scan_station(self, station_icao: str) -> bool:
        return station_icao == "KMIA"

    async def _fetch_market_keys(self, redis: RedisClient, station_icao: str) -> List[str]:
        schema = get_schema_config()
        raw_keys = await ensure_awaitable(redis.keys(f"{schema.kalshi_weather_prefix}:*fl*"))
        return [key.decode("utf-8") if isinstance(key, bytes) else key for key in raw_keys]

    async def _collect_states(self, redis: RedisClient, market_keys: List[str]) -> List[MarketState]:
        states: List[MarketState] = []
        for market_key in market_keys:
            if self._should_skip_market(market_key):
                continue
            decoded_data = await self._load_market_hash(redis, market_key)
            if not decoded_data:
                continue
            market_ticker = self._parse_market_ticker(market_key)
            if not market_ticker:
                continue
            states.append(self._build_market_state(decoded_data, market_ticker))
        return states

    def _should_skip_market(self, market_key: str) -> bool:
        return ":trading_signal" in market_key or ":position_state" in market_key

    async def _load_market_hash(self, redis: RedisClient, market_key: str) -> Dict[str, str]:
        market_data = await ensure_awaitable(redis.hgetall(market_key))
        if not market_data:
            return {}
        return {
            (k.decode("utf-8") if isinstance(k, bytes) else k): (v.decode("utf-8") if isinstance(v, bytes) else v)
            for k, v in market_data.items()
        }

    def _parse_market_ticker(self, market_key: str) -> Optional[str]:
        try:
            return parse_kalshi_market_key(market_key).ticker
        except ValueError:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            logger.warning("Expected data validation or parsing failure")
            return None

    def _build_market_state(self, decoded: Dict[str, str], market_ticker: str) -> MarketState:
        traded_value = decoded.get("traded")
        if traded_value is not None:
            traded_flag = str(traded_value).lower() == "true"
        else:
            traded_flag = False
        return MarketState(
            timestamp=datetime.now(timezone.utc),
            market_ticker=market_ticker,
            yes_bid=self.safe_float(decoded.get("yes_bid")),
            yes_ask=self.safe_float(decoded.get("yes_ask")),
            traded=traded_flag,
            min_strike_price_cents=self.safe_float(decoded.get("floor_strike")),
            max_strike_price_cents=self.safe_float(decoded.get("cap_strike")),
        )
