"""
Store method implementations extracted from store.py.

This module contains the main business logic methods from KalshiStore.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import orjson

from common.truthy import pick_if, pick_truthy

from ... import time_utils
from ...config.redis_schema import get_schema_config
from ...redis_schema import parse_kalshi_market_key
from ..error_types import REDIS_ERRORS
from .utils_market import _resolve_market_strike

SCHEMA = get_schema_config()
STRIKE_MATCH_TOLERANCE = 0.001

logger = logging.getLogger(__name__)


async def get_markets_by_currency(store, currency: str) -> List[Dict[str, Any]]:
    """Return market records for a currency."""
    if not await store._ensure_redis_connection():
        raise RuntimeError("Failed to ensure Redis connection for get_markets_by_currency")

    tickers = await store._find_currency_market_tickers(currency)
    if not tickers:
        store.logger.debug("No Kalshi market data found for %s in Redis", currency)
        return []

    metadata_extractor = getattr(store._reader, "_metadata_extractor", None)
    ticker_parser = getattr(store._reader, "_ticker_parser", None)
    if metadata_extractor is None or ticker_parser is None:
        raise RuntimeError("KalshiStore reader missing metadata extraction helpers")

    redis = await store._get_redis()
    from .reader_helpers.market_record_builder import build_market_records

    results, skip_reasons = await build_market_records(
        redis=redis,
        market_tickers=tickers,
        currency=currency,
        ticker_parser=ticker_parser,
        metadata_extractor=metadata_extractor,
        get_market_key_func=store.get_market_key,
        logger_instance=store.logger,
    )
    if skip_reasons:
        for reason, count in skip_reasons.most_common(5):
            store.logger.debug("Skipped %s markets for %s due to %s", count, currency, reason)
    return results


async def get_all_markets(store) -> List[Dict[str, Any]]:
    """Return all market records."""
    if not await store._ensure_redis_connection():
        raise RuntimeError("Failed to ensure Redis connection for get_all_markets")

    tickers = await store._find_all_market_tickers()
    if not tickers:
        store.logger.debug("No Kalshi market data found in Redis")
        return []

    metadata_extractor = getattr(store._reader, "_metadata_extractor", None)
    ticker_parser = getattr(store._reader, "_ticker_parser", None)
    if metadata_extractor is None or ticker_parser is None:
        raise RuntimeError("KalshiStore reader missing metadata extraction helpers")

    redis = await store._get_redis()
    from .reader_helpers.market_record_builder import build_market_records

    results, skip_reasons = await build_market_records(
        redis=redis,
        market_tickers=tickers,
        currency=None,
        ticker_parser=ticker_parser,
        metadata_extractor=metadata_extractor,
        get_market_key_func=store.get_market_key,
        logger_instance=store.logger,
    )
    if skip_reasons:
        for reason, count in skip_reasons.most_common(5):
            store.logger.debug("Skipped %s markets due to %s", count, reason)
    return results


async def get_active_strikes_and_expiries(store, currency: str) -> Dict[str, List[Dict]]:
    """Group active markets by expiry/strike for a currency."""
    from .store_initializer import KalshiStoreError

    markets = await store.get_markets_by_currency(currency)
    if not markets:
        raise KalshiStoreError(f"No active Kalshi markets found for currency {currency}")
    if not hasattr(store, "_reader"):
        raise RuntimeError("KalshiStore reader is not initialized for strike aggregation")
    aggregator = getattr(store._reader, "_market_aggregator", None)
    if aggregator is None:
        raise RuntimeError("KalshiStore missing market aggregator dependency")
    grouped, market_by_ticker = aggregator.aggregate_markets_by_point(markets)
    summary = aggregator.build_strike_summary(grouped, market_by_ticker)
    store.logger.debug("Aggregated %s expiry buckets for %s", len(summary), currency)
    return summary


async def get_interpolation_results(store, currency: str) -> Dict[str, Dict[str, Any]]:
    """Return interpolation data for all Kalshi markets matching the currency."""
    import sys

    try:
        package_module = sys.modules.get("common.redis_protocol.kalshi_store")
        module_logger = getattr(package_module, "logger", logger)
        if not await store._ensure_redis_connection():
            module_logger.error("Failed to ensure Redis connection for get_interpolation_results")
            return {}

        market_keys = await store._scan_market_keys()
        if not market_keys:
            module_logger.warning("No Kalshi markets found in Redis")
            return {}

        redis = await store._get_redis()
        currency_upper = currency.upper()
        results: Dict[str, Dict[str, Any]] = {}

        for market_key_str in market_keys:
            market_result = await _process_market_for_interpolation(store, market_key_str, currency_upper, redis, module_logger)
            if market_result is not None:
                ticker, data = market_result
                results[ticker] = data
    except REDIS_ERRORS as exc:  # Expected exception in operation  # policy_guard: allow-silent-handler
        module_logger = getattr(sys.modules.get("common.redis_protocol.kalshi_store"), "logger", logger)
        module_logger.error(
            "Redis error getting interpolation results for %s: %s",
            currency,
            exc,
            exc_info=True,
        )
        return {}
    else:
        return results


def _validate_market_for_interpolation(market_key_str: str, currency_upper: str, module_logger: Any) -> Optional[Tuple[str, str]]:
    """Validate market key and extract ticker."""
    try:
        descriptor = parse_kalshi_market_key(market_key_str)
    except ValueError as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        logger.warning("Failed to parse market key for interpolation: market_key_str=%r, error=%s", market_key_str, exc)
        return None
    market_ticker = descriptor.ticker
    if currency_upper not in market_ticker.upper():
        return None
    return market_key_str, market_ticker


def _parse_bid_ask_prices(
    yes_bid: Any, yes_ask: Any, market_ticker: str, module_logger: Any
) -> Optional[Tuple[Optional[float], Optional[float]]]:
    """Parse and validate bid/ask prices."""
    if yes_bid is None and yes_ask is None:
        return None
    try:
        yes_bid_float = float(yes_bid) if yes_bid is not None else None
        yes_ask_float = float(yes_ask) if yes_ask is not None else None
    except (ValueError, TypeError) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        module_logger.warning(
            "Skipping market %s with invalid bid/ask: %s / %s (%s)",
            market_ticker,
            yes_bid,
            yes_ask,
            exc,
        )
        return None
    else:
        return yes_bid_float, yes_ask_float


async def _process_market_for_interpolation(
    store, market_key_str: str, currency_upper: str, redis: Any, module_logger: Any
) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Process a single market for interpolation results."""
    validation_result = _validate_market_for_interpolation(market_key_str, currency_upper, module_logger)
    if validation_result is None:
        return None
    _, market_ticker = validation_result

    market_data = await redis.hgetall(market_key_str)
    if not market_data:
        return None

    yes_bid = market_data.get("t_yes_bid")
    yes_ask = market_data.get("t_yes_ask")
    price_result = _parse_bid_ask_prices(yes_bid, yes_ask, market_ticker, module_logger)
    if price_result is None:
        return None
    yes_bid_float, yes_ask_float = price_result

    try:
        interpolation_fields = _extract_interpolation_fields(store, market_data)
    except (ValueError, TypeError) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        module_logger.warning("Error parsing interpolation results for %s: %s", market_ticker, exc)
        return None

    return market_ticker, {
        "t_yes_bid": yes_bid_float,
        "t_yes_ask": yes_ask_float,
        **interpolation_fields,
    }


def _extract_interpolation_fields(store, market_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and parse interpolation-related fields from market data."""
    return {
        "interpolation_method": store._string_or_default(market_data.get("interpolation_method")),
        "deribit_points_used": store._int_or_default(market_data.get("deribit_points_used"), None),
        "interpolation_quality_score": store._float_or_default(market_data.get("interpolation_quality_score"), 0.0),
        "interpolation_timestamp": store._string_or_default(market_data.get("interpolation_timestamp")),
        "interp_error_bid": store._float_or_default(market_data.get("interp_error_bid"), 0.0),
        "interp_error_ask": store._float_or_default(market_data.get("interp_error_ask"), 0.0),
    }


async def get_market_data_for_strike_expiry(store, currency: str, expiry_date: str, strike: float) -> Optional[Dict[str, Any]]:
    """Return best bid/ask data for a strike/expiry pair."""
    setup_result = await _setup_strike_expiry_search(store)
    if setup_result is None:
        return None
    subscribed, metadata_extractor, redis = setup_result

    currency_upper = currency.upper()
    for market_ticker in subscribed:
        if currency_upper not in market_ticker.upper():
            continue
        market_data = await _get_matching_market_data(store, market_ticker, expiry_date, strike, redis, metadata_extractor)
        if market_data is not None:
            return market_data
    return None


async def _setup_strike_expiry_search(store) -> Optional[Tuple[List[str], Any, Any]]:
    """Setup dependencies for strike/expiry search."""
    if not await store._ensure_redis_connection():
        logger.error("Failed to ensure Redis connection for get_market_data_for_strike_expiry")
        return None

    subscribed = await store.get_subscribed_markets()
    if not subscribed:
        return None

    if not hasattr(store, "_reader"):
        raise RuntimeError("KalshiStore reader is not initialized")
    metadata_extractor = getattr(store._reader, "_metadata_extractor", None)
    if metadata_extractor is None:
        raise RuntimeError("KalshiStore missing metadata extractor dependency")

    redis = await store._get_redis()
    return subscribed, metadata_extractor, redis


async def _get_matching_market_data(
    store,
    market_ticker: str,
    expiry_date: str,
    strike: float,
    redis: Any,
    metadata_extractor: Any,
) -> Optional[Dict[str, Any]]:
    """Get market data if it matches the strike and expiry."""
    market_key = store.get_market_key(market_ticker)
    market_hash = await redis.hgetall(market_key)
    if not market_hash:
        return None

    snapshot = metadata_extractor.normalize_hash(market_hash)
    combined = _build_combined_metadata(snapshot, market_ticker)

    if not _matches_strike_expiry(combined, expiry_date, strike, market_ticker):
        return None

    return _extract_market_quote(snapshot, combined, market_ticker, metadata_extractor)


def _build_combined_metadata(snapshot: Dict[str, Any], market_ticker: str) -> Dict[str, Any]:
    """Combine metadata JSON with snapshot data."""
    metadata_payload = snapshot.get("metadata")
    metadata: Dict[str, Any] = {}
    if metadata_payload:
        try:
            metadata = orjson.loads(metadata_payload)
        except orjson.JSONDecodeError:  # Expected exception in operation  # policy_guard: allow-silent-handler
            logger.debug("Failed to decode metadata JSON for %s", market_ticker)
    return {**metadata, **snapshot}


def _matches_strike_expiry(combined: Dict[str, Any], expiry_date: str, strike: float, market_ticker: str) -> bool:
    """Check if market matches the target strike and expiry."""
    market_expiry = combined.get("close_time")
    if not market_expiry:
        logger.warning(
            "Market %s missing close_time in get_market_data_for_strike_expiry",
            market_ticker,
        )
        return False
    market_strike = _resolve_market_strike(combined)
    if market_strike is None:
        _none_guard_value = False
        return _none_guard_value
    return market_expiry == expiry_date and abs(float(market_strike) - strike) < STRIKE_MATCH_TOLERANCE


def _extract_market_quote(
    snapshot: Dict[str, Any],
    combined: Dict[str, Any],
    market_ticker: str,
    metadata_extractor: Any,
) -> Dict[str, Any]:
    """Extract bid/ask quotes with orderbook size."""
    best_bid, best_ask = metadata_extractor.extract_market_prices(combined)
    best_bid_size = snapshot.get("yes_bid_size")
    best_ask_size = snapshot.get("yes_ask_size")

    orderbook_payload = snapshot.get("orderbook")
    if orderbook_payload:
        try:
            orderbook = orjson.loads(orderbook_payload)
            yes_bids = pick_truthy(orderbook.get("yes_bids"), {})
            yes_asks = pick_truthy(orderbook.get("yes_asks"), {})
            if yes_bids and best_bid_size is None:
                best_bid_size = next(iter(yes_bids.values()))
            if yes_asks and best_ask_size is None:
                best_ask_size = next(iter(yes_asks.values()))
        except orjson.JSONDecodeError:  # Expected exception in operation  # policy_guard: allow-silent-handler
            logger.debug("Invalid orderbook payload for %s", market_ticker)

    return {
        "market_ticker": market_ticker,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "best_bid_size": best_bid_size,
        "best_ask_size": best_ask_size,
    }


async def is_market_expired(store, market_ticker: str) -> bool:
    """Check whether a market's close_time has already passed."""
    if not await store._ensure_redis_connection():
        logger.error("Failed to ensure Redis connection for is_market_expired %s", market_ticker)
        return False
    market_key = store.get_market_key(str(market_ticker))
    redis = await store._get_redis()
    market_data = await redis.hgetall(market_key)
    if not market_data:
        return False
    close_time_raw = market_data.get("close_time")
    if isinstance(close_time_raw, bytes):
        close_time_value = close_time_raw.decode("utf-8")
    else:
        close_time_value = pick_if(close_time_raw, lambda: str(close_time_raw), lambda: "")
    if not close_time_value:
        return False
    try:
        close_dt = datetime.fromisoformat(close_time_value.replace("Z", "+00:00"))
    except ValueError as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        logger.warning(
            "Failed to parse close time as ISO format: market_ticker=%r, close_time_value=%r, error=%s",
            market_ticker,
            close_time_value,
            exc,
        )
        return False
    current_time = time_utils.get_current_utc()
    return close_dt < current_time


def _parse_strike_values(floor_strike, cap_strike) -> tuple[Optional[float], Optional[float]]:
    """
    Parse floor and cap strike values.

    Delegates to common.strike_helpers.parse_strike_bounds.
    """
    from common.strike_helpers import parse_strike_bounds

    return parse_strike_bounds(floor_strike, cap_strike)


def _calculate_strike_from_type(strike_type: str, floor_value: Optional[float], cap_value: Optional[float]) -> Optional[float]:
    """
    Calculate strike based on type and values.

    Delegates to common.strike_helpers.calculate_strike_value.
    """
    from common.strike_helpers import calculate_strike_value

    return calculate_strike_value(strike_type, floor_value, cap_value)
