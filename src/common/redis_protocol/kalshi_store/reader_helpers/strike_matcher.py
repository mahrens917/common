"""
Strike Matcher - Match markets by strike and expiry

Handles matching logic for finding markets with specific strike/expiry combinations.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from redis.asyncio import Redis

from ...typing import ensure_awaitable

logger = logging.getLogger(__name__)


# Constants
_CONST_0_001 = 0.001


@dataclass(frozen=True)
class MarketMatcherDependencies:
    """Dependencies for market matching operations."""

    redis: Redis
    currency: str
    expiry: str
    strike: float
    markets: Any
    get_market_key_func: Callable
    ticker_parser: Any
    metadata_extractor: Any
    orderbook_reader: Any


async def find_matching_market(deps: MarketMatcherDependencies) -> Optional[Dict]:
    """
    Find market data matching strike/expiry criteria

    Args:
        deps: Dependencies for market matching operations

    Returns:
        Market data dict or None if not found
    """
    for market_ticker in deps.ticker_parser.iter_currency_markets(deps.markets, deps.currency):
        market_data = await ensure_awaitable(deps.redis.hgetall(deps.get_market_key_func(market_ticker)))
        metadata = deps.metadata_extractor.parse_market_metadata(market_ticker, market_data)
        if metadata is None:
            continue

        market_expiry = metadata.get("close_time")
        if not market_expiry:
            logger.warning(
                "Market %s missing close_time in find_matching_market",
                market_ticker,
            )
            continue

        market_strike = deps.metadata_extractor.resolve_market_strike(metadata)
        if not _matches_strike_expiry(market_strike, market_expiry, deps.strike, deps.expiry):
            continue

        best_bid, best_ask = deps.metadata_extractor.extract_market_prices(metadata)
        best_bid_size, best_ask_size = deps.orderbook_reader.extract_orderbook_sizes(market_ticker, market_data)

        return {
            "market_ticker": market_ticker,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "best_bid_size": best_bid_size,
            "best_ask_size": best_ask_size,
            "expiry": market_expiry,
            "strike": market_strike,
        }

    return None


def _matches_strike_expiry(
    market_strike: Optional[float],
    market_expiry: str,
    target_strike: float,
    target_expiry: str,
) -> bool:
    """
    Check if market matches target strike and expiry

    Args:
        market_strike: Market strike price
        market_expiry: Market expiry date
        target_strike: Target strike price
        target_expiry: Target expiry date

    Returns:
        True if market matches criteria
    """
    if market_strike is None:
        _none_guard_value = False
        return _none_guard_value
    if market_expiry != target_expiry:
        return False
    if abs(market_strike - target_strike) >= _CONST_0_001:
        return False
    return True
