from __future__ import annotations

"""Market filtering logic for Kalshi catalog."""

import logging
import re
import time
from typing import Dict, List, Optional, Set, Tuple

from .market_filter_helpers.close_time_validator import CloseTimeValidator
from .market_filter_helpers.crypto_pattern_matcher import (
    token_matches_asset,
    token_matches_crypto,
    value_matches_crypto,
)
from .market_filter_helpers.weather_filter import WeatherFilter

logger = logging.getLogger(__name__)


CRYPTO_ASSETS: tuple[str, ...] = ("BTC", "ETH")
CRYPTO_TICKER_PREFIXES: tuple[str, ...] = ("BTC", "ETH", "KXBTC", "KXETH")
CRYPTO_FIELD_CANDIDATES: tuple[str, ...] = (
    "currency",
    "underlying",
    "underlying_symbol",
    "underlying_asset",
    "asset",
    "series_ticker",
    "product_ticker",
)
TOKEN_SPLIT_PATTERN = re.compile(r"[^A-Z0-9]+")
CRYPTO_MONTH_PATTERN = re.compile(r"\d{2}(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\d{2}")
VALID_CRYPTO_STRIKE_TYPES: tuple[str, ...] = (
    "greater",
    "less",
    "greater_or_equal",
    "less_or_equal",
    "between",
)


def _value_matches_crypto(value: str) -> bool:
    return value_matches_crypto(value)


def _token_matches_crypto(token: str) -> bool:
    return token_matches_crypto(token)


def _token_matches_asset(token: str, asset: str) -> bool:
    return token_matches_asset(token, asset)


def _close_time_in_future(market: Dict[str, object], now_ts: float) -> bool:
    return CloseTimeValidator.is_in_future(market, now_ts)


def _create_empty_stats() -> Dict[str, int]:
    return {
        "crypto_total": 0,
        "crypto_kept": 0,
        "weather_total": 0,
        "weather_kept": 0,
        "other_total": 0,
    }


def _is_valid_market(market: object) -> bool:
    if not isinstance(market, dict):
        return False
    ticker = str(market.get("ticker") or "")
    return bool(ticker)


def _is_weather_market(category: Optional[object], ticker: str) -> bool:
    return category in {"Weather", "Climate and Weather"} or ticker.startswith("KXHIGH")


def _extract_weather_station_token(ticker: str) -> Optional[str]:
    return WeatherFilter.extract_station_token(ticker)


def _passes_weather_filters(market: Dict[str, object], now_ts: float, weather_tokens: Set[str]) -> bool:
    weather_filter = WeatherFilter(weather_tokens)
    return weather_filter.passes_filters(market, now_ts, CloseTimeValidator)


def _process_market_entry(
    market: Dict[str, object],
    filtered: List[Dict[str, object]],
    stats: Dict[str, int],
    now_ts: float,
    crypto_validator: "CryptoMarketValidator",
    weather_tokens: Set[str],
) -> None:
    category = market.get("__category")
    ticker = str(market.get("ticker") or "")

    if category == "Crypto" or crypto_validator.is_crypto_market(market):
        stats["crypto_total"] += 1
        if crypto_validator.passes_crypto_filters(market, now_ts):
            filtered.append(market)
            stats["crypto_kept"] += 1
        return

    if _is_weather_market(category, ticker):
        stats["weather_total"] += 1
        if _passes_weather_filters(market, now_ts, weather_tokens):
            filtered.append(market)
            stats["weather_kept"] += 1
        return

    stats["other_total"] += 1


class CryptoMarketValidator:
    """Validates crypto-related markets."""

    def is_crypto_market(self, market: Dict[str, object]) -> bool:
        if self._ticker_matches_crypto(market):
            return True
        return self._fields_match_crypto(market)

    def passes_crypto_filters(self, market: Dict[str, object], now_ts: float) -> bool:
        ticker = self._normalized_ticker(market)
        if not ticker:
            return False
        validators = (
            self._contains_crypto_asset(ticker),
            self._contains_month_code(ticker),
            _close_time_in_future(market, now_ts),
            self._has_valid_strike_type(market),
            self._has_valid_strike_bounds(market),
        )
        return all(validators)

    def _ticker_matches_crypto(self, market: Dict[str, object]) -> bool:
        ticker = market.get("ticker")
        return isinstance(ticker, str) and _value_matches_crypto(ticker)

    def _fields_match_crypto(self, market: Dict[str, object]) -> bool:
        for field in CRYPTO_FIELD_CANDIDATES:
            value = market.get(field)
            if isinstance(value, str) and _value_matches_crypto(value):
                return True
        return False

    def _normalized_ticker(self, market: Dict[str, object]) -> str:
        return str(market.get("ticker") or "").upper()

    def _contains_crypto_asset(self, ticker: str) -> bool:
        return any(asset in ticker for asset in CRYPTO_ASSETS)

    def _contains_month_code(self, ticker: str) -> bool:
        return bool(CRYPTO_MONTH_PATTERN.search(ticker))

    def _has_valid_strike_type(self, market: Dict[str, object]) -> bool:
        strike_type = market.get("strike_type")
        return strike_type in VALID_CRYPTO_STRIKE_TYPES

    def _has_valid_strike_bounds(self, market: Dict[str, object]) -> bool:
        cap_strike = market.get("cap_strike")
        floor_strike = market.get("floor_strike")
        if cap_strike is None and floor_strike is None:
            return False
        if cap_strike is not None and floor_strike is not None and cap_strike == floor_strike:
            return False
        return True


class MarketFilter:
    """Filters markets by type (crypto, weather) and validates criteria."""

    def __init__(self, weather_station_tokens: Set[str]) -> None:
        self._weather_station_tokens = weather_station_tokens
        self._crypto_validator = CryptoMarketValidator()

    def filter_markets(self, markets: List[Dict[str, object]]) -> Tuple[List[Dict[str, object]], Dict[str, int]]:
        """Filter markets and return filtered list with stats."""
        filtered: List[Dict[str, object]] = []
        stats = _create_empty_stats()
        now_ts = time.time()

        for market in markets:
            if not _is_valid_market(market):
                continue
            _process_market_entry(
                market,
                filtered,
                stats,
                now_ts,
                self._crypto_validator,
                self._weather_station_tokens,
            )

        return filtered, stats
