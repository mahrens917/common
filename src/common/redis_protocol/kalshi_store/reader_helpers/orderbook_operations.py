"""Orderbook operations for KalshiMarketReader."""

from typing import Any, Callable, Dict


async def get_orderbook_with_connection_check(
    conn_wrapper: Any,
    orderbook_reader: Any,
    ticker: str,
    get_market_key_fn: Callable[[str], str],
) -> Dict:
    """Get orderbook with connection check."""
    if not await conn_wrapper.ensure_connection():
        return {}
    return await orderbook_reader.get_orderbook(
        await conn_wrapper.get_redis(), get_market_key_fn(ticker), ticker
    )


async def get_orderbook_side_with_connection_check(
    conn_wrapper: Any,
    orderbook_reader: Any,
    ticker: str,
    side: str,
    get_market_key_fn: Callable[[str], str],
) -> Dict:
    """Get orderbook side with connection check."""
    if not await conn_wrapper.ensure_connection():
        return {}
    return await orderbook_reader.get_orderbook_side(
        await conn_wrapper.get_redis(), get_market_key_fn(ticker), ticker, side
    )
