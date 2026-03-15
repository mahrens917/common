"""Build a station manifest from Kalshi weather market Redis keys.

Pure logic for parsing weather market tickers, resolving ICAO station codes,
and assembling the manifest dict. No Redis or S3 I/O — callers fetch keys
(sync or async) and handle uploads themselves.
"""

from __future__ import annotations

import logging
from calendar import monthrange as _monthrange
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

from common.config.weather import load_market_code_mapping
from common.redis_schema.kalshi import _classify_kalshi_ticker
from common.redis_schema.markets import KalshiMarketCategory

logger = logging.getLogger(__name__)

MARKET_KEY_PATTERN = "markets:kalshi:weather:*"
S3_MANIFEST_KEY = "config/market_manifest.json"

_MONTH_ABBREVS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}
_YEAR_PREFIX_LEN = 2
_MONTH_ABBREV_LEN = 3
_MIN_EXPIRY_LEN = 7
_KEY_PART_COUNT = 4


def _parse_expiry_date(expiry_token: str) -> Optional[datetime]:
    """Parse a Kalshi expiry token like '26MAR14' into a UTC datetime.

    Format: YYMONDD where MON is a 3-letter month abbreviation.
    """
    date_part = expiry_token.split("T")[0] if "T" in expiry_token else expiry_token
    if len(date_part) < _MIN_EXPIRY_LEN:
        return None
    year_str = date_part[:_YEAR_PREFIX_LEN]
    month_str = date_part[_YEAR_PREFIX_LEN : _YEAR_PREFIX_LEN + _MONTH_ABBREV_LEN]
    day_str = date_part[_YEAR_PREFIX_LEN + _MONTH_ABBREV_LEN :]
    month_num = _MONTH_ABBREVS.get(month_str.upper())
    if month_num is None:
        return None
    if not year_str.isdigit() or not day_str.isdigit():
        return None
    year = 2000 + int(year_str)
    day = int(day_str)
    _, max_day = _monthrange(year, month_num)
    if day < 1 or day > max_day:
        return None
    return datetime(year, month_num, day, tzinfo=timezone.utc)


def _determine_horizon(expiry_date: datetime) -> Optional[int]:
    """Return 0 for today's market, 1 for tomorrow's, None otherwise."""
    today = datetime.now(timezone.utc).date()
    tomorrow = today + timedelta(days=1)
    market_date = expiry_date.date()
    if market_date == today:
        return 0
    if market_date == tomorrow:
        return 1
    return None


def _default_station_flags() -> Dict[str, bool]:
    return {"high_h0": False, "high_h1": False, "low_h0": False, "low_h1": False}


def _decode_key(raw_key: Any) -> str:
    """Decode a raw Redis key to string."""
    return raw_key.decode("utf-8") if isinstance(raw_key, bytes) else raw_key


def _extract_ticker(key: str) -> Optional[str]:
    """Extract the ticker from a colon-delimited Redis key."""
    parts = key.split(":")
    if len(parts) != _KEY_PART_COUNT:
        return None
    return parts[3]


def _resolve_station_market(
    ticker: str,
    market_code_mapping: Dict[str, str],
) -> Optional[tuple[str, str]]:
    """Classify a ticker and resolve its ICAO station code and market flag key.

    Returns (icao, market_key) or None if the ticker is not a valid weather market.
    """
    category, underlying, expiry_token = _classify_kalshi_ticker(ticker)
    if category != KalshiMarketCategory.WEATHER:
        return None
    if underlying is None or expiry_token is None:
        return None

    icao = market_code_mapping.get(underlying)
    if icao is None:
        logger.debug("Unknown underlying %r from ticker %s", underlying, ticker)
        return None

    expiry_date = _parse_expiry_date(expiry_token)
    if expiry_date is None:
        return None

    horizon = _determine_horizon(expiry_date)
    if horizon is None:
        return None

    if ticker.startswith("KXLOW"):
        event_type = "low"
    else:
        event_type = "high"
    return icao, f"{event_type}_h{horizon}"


def build_market_manifest(raw_keys: List[str]) -> Dict[str, Any]:
    """Build a market manifest dict from a list of Redis key strings.

    Args:
        raw_keys: Redis keys matching ``markets:kalshi:weather:*``.
            May be str or bytes; bytes are decoded as UTF-8.

    Returns:
        Manifest dict with ``generated_at`` and ``stations`` keys.
    """
    market_code_mapping = load_market_code_mapping()
    stations: Dict[str, Dict[str, bool]] = {}
    seen_icaos: Set[str] = set()

    for raw_key in raw_keys:
        ticker = _extract_ticker(_decode_key(raw_key))
        if ticker is None:
            continue

        result = _resolve_station_market(ticker, market_code_mapping)
        if result is None:
            continue

        icao, market_key = result
        seen_icaos.add(icao)
        if icao not in stations:
            stations[icao] = _default_station_flags()
        stations[icao][market_key] = True

    for icao in seen_icaos:
        if icao not in stations:
            stations[icao] = _default_station_flags()

    logger.info("Market manifest: %d stations discovered", len(stations))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stations": dict(sorted(stations.items())),
    }
