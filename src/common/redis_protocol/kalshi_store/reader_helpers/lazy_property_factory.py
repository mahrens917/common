"""Lazy initialization factory for KalshiMarketReader helper components."""

from typing import Any, Callable


def create_status_checker(
    conn_wrapper: Any,
    ticker_parser: Any,
    expiry_checker: Any,
    get_market_key_fn: Callable[[str], str],
) -> Any:
    """Create MarketStatusChecker instance."""
    from ..reader import MarketStatusChecker

    return MarketStatusChecker(conn_wrapper, ticker_parser, expiry_checker, get_market_key_fn)


def create_snapshot_retriever(conn_wrapper: Any, snapshot_reader: Any, get_market_key_fn: Callable[[str], str]) -> Any:
    """Create SnapshotRetriever instance."""
    from ..reader import SnapshotRetriever

    return SnapshotRetriever(conn_wrapper, snapshot_reader, get_market_key_fn)


def create_query_handler(
    conn_wrapper: Any,
    market_lookup: Any,
    market_filter: Any,
    market_aggregator: Any,
    snapshot_reader: Any,
    logger: Any,
    get_market_key_fn: Callable[[str], str],
) -> Any:
    """Create MarketQueryHandler instance."""
    from ..reader import MarketQueryHandler

    return MarketQueryHandler(
        conn_wrapper,
        market_lookup,
        market_filter,
        market_aggregator,
        snapshot_reader,
        logger,
        get_market_key_fn,
    )
