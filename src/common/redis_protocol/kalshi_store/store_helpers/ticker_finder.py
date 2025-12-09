"""Ticker finding helpers for KalshiStore."""

from typing import List


async def find_currency_market_tickers(store, currency: str) -> List[str]:
    """Locate Kalshi market tickers for a currency using the reader's market filter."""
    if not hasattr(store, "_reader"):
        raise RuntimeError("KalshiStore reader is not initialized")
    redis = await store._get_redis()
    market_filter = getattr(store._reader, "_market_filter", None)
    ticker_parser = getattr(store._reader, "_ticker_parser", None)
    if market_filter is None or ticker_parser is None:
        raise RuntimeError("KalshiStore reader missing market filter dependencies")
    return await market_filter.find_currency_market_tickers(
        redis, currency, ticker_parser.is_market_for_currency
    )
