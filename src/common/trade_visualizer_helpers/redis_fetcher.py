"""Redis data fetching for trade visualization."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from common.config.redis_schema import TradeKeys
from common.redis_protocol.trade_store import TradeStore

from .liquidity_fetcher import MarketState

logger = logging.getLogger(__name__)


class RedisFetcher:
    """Fetches trade and market data from Redis."""

    def __init__(self, trade_store: TradeStore):
        self._trade_store = trade_store

    async def get_executed_trades_for_station(self, redis, station_icao: str, start_time: datetime, end_time: datetime):
        """Fetch executed trades for a station from Redis."""
        station_key = TradeKeys.by_station(station_icao)
        raw_order_ids = await redis.smembers(station_key)
        start_aware = start_time if start_time.tzinfo else start_time.replace(tzinfo=timezone.utc)
        end_aware = end_time if end_time.tzinfo else end_time.replace(tzinfo=timezone.utc)
        results = []
        for raw in raw_order_ids:
            order_id = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            trade = await self._trade_store.get_trade_by_order_id(order_id)
            if not trade:
                continue
            trade_time = trade.trade_timestamp if trade.trade_timestamp.tzinfo else trade.trade_timestamp.replace(tzinfo=timezone.utc)
            if start_aware <= trade_time <= end_aware:
                results.append(trade)
        return results

    async def get_market_liquidity_states(self, redis, station_icao: str, start_time: datetime, end_time: datetime) -> List[MarketState]:
        """Fetch market liquidity states from Redis."""
        if station_icao != "KMIA":
            return []

        raw_keys = await self._fetch_market_keys(redis)
        states = await self._process_market_keys(redis, raw_keys)
        return states

    async def _fetch_market_keys(self, redis) -> list:
        """Fetch matching market keys from Redis."""
        from common import trade_visualizer

        schema = trade_visualizer.get_schema_config()
        pattern = f"{schema.kalshi_weather_prefix}:*fl*"
        return await redis.keys(pattern)

    async def _process_market_keys(self, redis, raw_keys: list) -> List[MarketState]:
        """Process market keys and extract states."""
        states: List[MarketState] = []
        for raw_key in raw_keys:
            key = raw_key.decode("utf-8") if isinstance(raw_key, bytes) else raw_key
            if self._is_auxiliary_key(key):
                continue

            state = await self._extract_market_state(redis, key)
            if state is not None:
                states.append(state)
        return states

    def _is_auxiliary_key(self, key: str) -> bool:
        """Check if key is an auxiliary key to skip."""
        return ":trading_signal" in key or ":position_state" in key

    async def _extract_market_state(self, redis, key: str) -> MarketState | None:
        """Extract market state from a single key."""
        market_data = await redis.hgetall(key)
        if not market_data:
            return None

        decoded = self._decode_market_data(market_data)
        ticker = self._extract_ticker(key)
        if ticker is None:
            return None

        return self._build_market_state(ticker, decoded)

    def _decode_market_data(self, market_data: dict) -> dict:
        """Decode bytes in market data to strings."""
        return {
            (k.decode("utf-8") if isinstance(k, bytes) else k): (v.decode("utf-8") if isinstance(v, bytes) else v)
            for k, v in market_data.items()
        }

    def _extract_ticker(self, key: str) -> str | None:
        """Extract ticker from market key."""
        try:
            from common import trade_visualizer

            return trade_visualizer.parse_kalshi_market_key(key).ticker
        except ValueError:
            return None

    def _build_market_state(self, ticker: str, decoded: dict) -> MarketState:
        """Build MarketState from decoded data."""
        traded_raw = decoded.get("traded")
        if traded_raw is None:
            raise ValueError(f"Market data for {ticker} missing 'traded' field")
        return MarketState(
            timestamp=datetime.now(timezone.utc),
            market_ticker=ticker,
            yes_bid=self._safe_float(decoded.get("yes_bid")),
            yes_ask=self._safe_float(decoded.get("yes_ask")),
            traded=str(traded_raw).lower() == "true",
            min_strike_price_cents=self._safe_float(decoded.get("floor_strike")),
            max_strike_price_cents=self._safe_float(decoded.get("cap_strike")),
        )

    def _safe_float(self, value):
        """Safely convert value to float."""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None
