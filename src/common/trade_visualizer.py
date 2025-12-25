from __future__ import annotations

"""Trade visualization helpers for weather temperature charts."""
import asyncio
import logging
from datetime import datetime
from typing import List

from matplotlib.axes import Axes

from common.config.redis_schema import get_schema_config
from common.redis_protocol.kalshi_store import KalshiStore
from common.redis_protocol.trade_store import TradeStore, TradeStoreError
from common.redis_schema import parse_kalshi_market_key as _parse_market_key

from .trade_visualizer_helpers import LiquidityFetcher, RedisFetcher, ShadingBuilder, TradeFetcher
from .trade_visualizer_helpers.liquidity_fetcher import MarketState
from .trade_visualizer_helpers.redis_helpers.connection import (
    get_redis_connection,
)
from .trade_visualizer_helpers.shading_builder import TradeShading
from .trade_visualizer_helpers.shading_creator import (
    create_executed_trade_shading,
    create_no_liquidity_shading,
    is_no_liquidity_state,
    safe_float,
)

logger = logging.getLogger(__name__)
parse_kalshi_market_key = _parse_market_key

# Default color constants
_DEFAULT_EXECUTED_BUY_COLOR = "#90EE90"
_DEFAULT_EXECUTED_SELL_COLOR = "#FFB6C1"
_DEFAULT_UNEXECUTED_COLOR = "#808080"
_DEFAULT_ALPHA = 0.3


def create_trade_visualizer() -> "TradeVisualizer":
    """Factory function to create TradeVisualizer with default dependencies."""
    trade_store = TradeStore()
    kalshi_store = KalshiStore()
    trade_fetcher = TradeFetcher(trade_store)
    liquidity_fetcher = LiquidityFetcher()
    shading_builder = ShadingBuilder()
    redis_fetcher = RedisFetcher(trade_store)
    return TradeVisualizer(
        trade_store=trade_store,
        kalshi_store=kalshi_store,
        trade_fetcher=trade_fetcher,
        liquidity_fetcher=liquidity_fetcher,
        shading_builder=shading_builder,
        redis_fetcher=redis_fetcher,
    )


__all__ = [
    "TradeVisualizer",
    "MarketState",
    "TradeShading",
    "get_redis_connection",
    "create_trade_visualizer",
    "get_schema_config",
]


class TradeVisualizerTestHooks:
    """Expose helpers for tests without bloating the main visualizer."""

    _shading_builder: ShadingBuilder
    _redis_fetcher: RedisFetcher
    _liquidity_fetcher: LiquidityFetcher

    def _create_executed_trade_shading(
        self,
        trade,
        kalshi_strikes: List[float],
        temperature_timestamps: List[datetime],
    ) -> TradeShading | None:
        """Expose shading builder for tests."""
        return create_executed_trade_shading(self._shading_builder, trade, kalshi_strikes, temperature_timestamps)

    def _create_no_liquidity_shading(
        self,
        state,
        kalshi_strikes: List[float],
        temperature_timestamps: List[datetime],
    ) -> TradeShading | None:
        """Expose no-liquidity shading builder for tests."""
        return create_no_liquidity_shading(self._shading_builder, state, kalshi_strikes, temperature_timestamps)

    def _is_no_liquidity_state(self, state) -> bool:
        """Expose liquidity state helper for tests."""
        return is_no_liquidity_state(self._shading_builder, state)

    async def _get_executed_trades_for_station(self, station_icao: str, start_time: datetime, end_time: datetime):
        """Fetch executed trades using the local Redis helper for tests."""
        redis = await get_redis_connection()
        try:
            return await self._redis_fetcher.get_executed_trades_for_station(redis, station_icao, start_time, end_time)
        finally:
            await redis.aclose()

    async def _get_market_liquidity_states(self, station_icao: str, start_time: datetime, end_time: datetime) -> List[MarketState]:
        """Fetch liquidity states using the Redis helper for tests."""
        redis = await get_redis_connection()
        try:
            return await self._redis_fetcher.get_market_liquidity_states(redis, station_icao, start_time, end_time)
        finally:
            await redis.aclose()

    def _safe_float(self, value):
        """Expose safe float conversion for tests."""
        return safe_float(self._liquidity_fetcher, value)


class TradeVisualizer(TradeVisualizerTestHooks):
    """Compute shaded regions that highlight executed trades and liquidity gaps."""

    def __init__(
        self,
        *,
        trade_store: TradeStore,
        kalshi_store: KalshiStore,
        trade_fetcher: TradeFetcher,
        liquidity_fetcher: LiquidityFetcher,
        shading_builder: ShadingBuilder,
        redis_fetcher: RedisFetcher,
    ) -> None:
        self._trade_store = trade_store
        self._kalshi_store = kalshi_store
        self._trade_fetcher = trade_fetcher
        self._liquidity_fetcher = liquidity_fetcher
        self._shading_builder = shading_builder
        self._redis_fetcher = redis_fetcher
        # Expose palette for tests/consumers
        self.EXECUTED_BUY_COLOR = getattr(shading_builder, "EXECUTED_BUY_COLOR", _DEFAULT_EXECUTED_BUY_COLOR)
        self.EXECUTED_SELL_COLOR = getattr(shading_builder, "EXECUTED_SELL_COLOR", _DEFAULT_EXECUTED_SELL_COLOR)
        self.UNEXECUTED_COLOR = getattr(shading_builder, "UNEXECUTED_COLOR", _DEFAULT_UNEXECUTED_COLOR)
        self.DEFAULT_ALPHA = getattr(shading_builder, "DEFAULT_ALPHA", _DEFAULT_ALPHA)

    async def initialize(self) -> bool:
        """Open the Redis-backed stores required for fetching trade information."""
        if not await self._trade_store.initialize():
            raise TradeStoreError("Failed to initialize Trade store for trade visualizer")
        if not await self._kalshi_store.initialize():
            raise RuntimeError("Failed to initialize Kalshi store for trade visualizer")
        return True

    async def close(self) -> None:
        """Release any Redis connections held by the helper."""
        await self._trade_store.close()
        await self._kalshi_store.close()

    async def get_trade_shadings_for_station(
        self,
        station_icao: str,
        start_time: datetime,
        end_time: datetime,
        temperature_timestamps: List[datetime],
        kalshi_strikes: List[float],
    ) -> List[TradeShading]:
        """Return shaded regions to overlay on the temperature chart for a station."""
        try:
            shadings: List[TradeShading] = []
            executed_trades = await self._get_executed_trades_for_station(station_icao, start_time, end_time)
            logger.info("Found %s executed trades for %s", len(executed_trades), station_icao)
            for trade in executed_trades:
                shading = self._create_executed_trade_shading(trade, kalshi_strikes, temperature_timestamps)
                if shading:
                    shadings.append(shading)
                    logger.info(
                        "Added %s trade shading at %.0f°F",
                        trade.trade_side.value,
                        float(trade.price_cents),
                    )
            liquidity_states = await self._get_market_liquidity_states(station_icao, start_time, end_time)
            for state in liquidity_states:
                if self._is_no_liquidity_state(state):
                    shading = self._create_no_liquidity_shading(state, kalshi_strikes, temperature_timestamps)
                    if shading:
                        shadings.append(shading)
                        logger.info("Added no-liquidity shading for %s", state.market_ticker)
        except asyncio.CancelledError:
            raise
        except (  # policy_guard: allow-silent-handler
            OSError,
            ConnectionError,
            RuntimeError,
            ValueError,
        ):  # pragma: no cover - defensive logging
            logger.exception("Failed to build trade shadings for %s", station_icao)
            return []
        else:
            return shadings

    def apply_trade_shadings_to_chart(self, ax: Axes, shadings: List[TradeShading], timestamps_for_chart: List[datetime]) -> None:
        """Apply trade shadings to matplotlib chart."""
        self._shading_builder.apply_trade_shadings_to_chart(ax, shadings, timestamps_for_chart)
