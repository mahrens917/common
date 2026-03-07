"""In-memory index of Deribit instruments maintained from stream updates.

Mirrors EventMarketIndex for Kalshi data. Keyed by Redis key
(e.g. ``markets:deribit:option:BTC:2025-03-28:50000:c``).
Built once at startup from a full OptimizedMarketStore scan, then
updated incrementally via ``apply_stream_update`` — no Redis IO on
the hot path.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from common.redis_schema.markets import DeribitInstrumentType

logger = logging.getLogger(__name__)

_SCAN_BATCH_SIZE = 10000


async def load_currency_keys(market_store: Any, currency: str) -> tuple[Any, set[str]]:
    """Scan Redis for all Deribit keys matching a currency."""
    redis_client = await market_store.get_redis_client()
    pattern = f"markets:deribit:*:{currency.upper()}*"
    keys: set[str] = set()
    cursor = 0
    while True:
        cursor, batch = await redis_client.scan(cursor=cursor, match=pattern, count=_SCAN_BATCH_SIZE)
        for k in batch:
            keys.add(k.decode("utf-8") if isinstance(k, bytes) else k)
        if cursor == 0:
            break
    return redis_client, keys


async def fetch_all_hashes(redis_client: Any, keys: list[str]) -> Dict[str, Dict[Any, Any]]:
    """Pipeline HGETALL for a list of keys. Returns key -> hash data mapping."""
    result: Dict[str, Dict[Any, Any]] = {}
    async with redis_client.pipeline() as pipe:
        for key in keys:
            pipe.hgetall(key)
        responses = await pipe.execute()
    for key, data in zip(keys, responses):
        result[key] = data
    return result


def _decode_hash(raw: Dict[Any, Any]) -> Dict[str, str]:
    """Decode Redis hash bytes to strings."""
    decoded: Dict[str, str] = {}
    for k, v in raw.items():
        str_key = k.decode("utf-8") if isinstance(k, bytes) else str(k)
        str_val = v.decode("utf-8") if isinstance(v, bytes) else str(v)
        decoded[str_key] = str_val
    return decoded


def register_loaded_data(
    data_map: Dict[str, Dict[Any, Any]],
    instruments: Dict[str, Dict[str, str]],
    register_key: Callable[[str, Dict[str, str]], None],
) -> None:
    """Decode and register all fetched instrument data into the index."""
    for key, data in data_map.items():
        if not data:
            continue
        decoded = _decode_hash(data)
        decoded["instrument_key"] = key
        instruments[key] = decoded
        register_key(key, decoded)


_RECONCILE_TOLERANCE = 5


async def _count_deribit_keys(redis: Any) -> int:
    """SCAN-count Redis keys matching Deribit market patterns."""
    count = 0
    for currency in ("BTC", "ETH"):
        pattern = f"markets:deribit:*:{currency}*"
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=10000)
            count += len(keys)
            if cursor == 0:
                break
    return count


_SPOT_INSTRUMENT_TYPE = DeribitInstrumentType.SPOT.value
_OPTION_INSTRUMENT_TYPE = DeribitInstrumentType.OPTION.value
_FUTURE_INSTRUMENT_TYPE = DeribitInstrumentType.FUTURE.value
_MIN_DERIBIT_KEY_PARTS = 4
_DERIBIT_TYPE_INDEX = 2
_DERIBIT_CURRENCY_INDEX = 3


class DeribitInstrumentIndex:
    """In-memory index: instrument_key -> market data for Deribit."""

    def __init__(self) -> None:
        self._instruments: Dict[str, Dict[str, str]] = {}
        self._by_type_currency: Dict[str, Dict[str, list[str]]] = {
            _SPOT_INSTRUMENT_TYPE: {},
            _OPTION_INSTRUMENT_TYPE: {},
            _FUTURE_INSTRUMENT_TYPE: {},
        }

    async def initialize(self, market_store: Any) -> None:
        """One-time full scan to populate index from Redis."""
        for currency in ("BTC", "ETH"):
            redis_client, keys = await load_currency_keys(market_store, currency)
            if not keys:
                continue
            data_map = await fetch_all_hashes(redis_client, list(keys))
            register_loaded_data(data_map, self._instruments, self._register_key)
        logger.info(
            "DeribitInstrumentIndex initialized: %d instruments",
            len(self._instruments),
        )

    def apply_stream_update(self, instrument_key: str, fields: Dict[str, str]) -> None:
        """Merge stream payload into in-memory cache. No Redis IO."""
        existing = self._instruments.get(instrument_key)
        if existing is not None:
            existing.update(fields)
            return

        entry: Dict[str, str] = {"instrument_key": instrument_key, **fields}
        self._instruments[instrument_key] = entry
        self._register_key(instrument_key, fields)

    def get_options_by_currency(self, currency: str) -> List[Dict[str, str]]:
        """Return cached option instruments for a currency."""
        return self._get_by_type(currency, _OPTION_INSTRUMENT_TYPE)

    def get_futures_by_currency(self, currency: str) -> List[Dict[str, str]]:
        """Return cached future instruments for a currency."""
        return self._get_by_type(currency, _FUTURE_INSTRUMENT_TYPE)

    def get_spot_price(self, currency: str) -> Optional[float]:
        """Return mid-price for the currency's spot pair, or None."""
        bid_ask = self.get_spot_bid_ask(currency)
        if bid_ask is None:
            return None
        bid, ask = bid_ask
        return (bid + ask) / 2

    def get_spot_bid_ask(self, currency: str) -> Optional[tuple[float, float]]:
        """Return (bid, ask) for the currency's spot pair, or None."""
        return _find_spot_bid_ask(self._by_type_currency, self._instruments, currency)

    @property
    def instrument_count(self) -> int:
        """Number of indexed instruments."""
        return len(self._instruments)

    async def reconcile(self, redis: Any) -> bool:
        """Compare cache count to Redis; return True if diverged."""
        redis_count = await _count_deribit_keys(redis)
        if abs(redis_count - self.instrument_count) <= _RECONCILE_TOLERANCE:
            return False
        logger.warning(
            "DeribitInstrumentIndex count divergence: cache=%d redis=%d — caller should re-initialize",
            self.instrument_count,
            redis_count,
        )
        return True

    def _get_by_type(self, currency: str, instrument_type: str) -> List[Dict[str, str]]:
        return _collect_instruments(self._by_type_currency, self._instruments, instrument_type, currency)

    def _register_key(self, instrument_key: str, fields: Dict[str, str]) -> None:
        """Classify and register a key by instrument type and currency."""
        instrument_type, currency = _resolve_type_and_currency(instrument_key, fields)
        if not instrument_type or not currency:
            return
        _add_to_bucket(self._by_type_currency, instrument_type, currency.upper(), instrument_key)


def _collect_instruments(
    by_type_currency: Dict[str, Dict[str, list[str]]],
    instruments: Dict[str, Dict[str, str]],
    instrument_type: str,
    currency: str,
) -> List[Dict[str, str]]:
    """Collect instrument dicts for a given type and currency."""
    if instrument_type not in by_type_currency:
        return []
    currency_bucket = by_type_currency[instrument_type]
    currency_upper = currency.upper()
    if currency_upper not in currency_bucket:
        return []
    return [instruments[k] for k in currency_bucket[currency_upper] if k in instruments]


_UNRESOLVED: tuple[None, None] = (None, None)


def _resolve_type_and_currency(instrument_key: str, fields: Dict[str, str]) -> tuple[Optional[str], Optional[str]]:
    """Extract instrument_type and currency from fields or key parsing."""
    instrument_type = fields.get("instrument_type")
    currency = fields.get("currency")
    if instrument_type and currency:
        return instrument_type, currency
    parsed = _safe_parse_key(instrument_key)
    if parsed is None:
        return _UNRESOLVED
    return instrument_type or parsed[0], currency or parsed[1]


def _safe_parse_key(instrument_key: str) -> Optional[tuple[str, str]]:
    """Parse a Deribit key, returning (type_value, currency) or None on failure."""
    parts = instrument_key.split(":")
    if len(parts) < _MIN_DERIBIT_KEY_PARTS or parts[0] != "markets" or parts[1] != "deribit":
        return None
    return parts[_DERIBIT_TYPE_INDEX], parts[_DERIBIT_CURRENCY_INDEX].upper()


def _add_to_bucket(
    by_type_currency: Dict[str, Dict[str, list[str]]],
    instrument_type: str,
    currency_upper: str,
    instrument_key: str,
) -> None:
    """Register a key in the type/currency bucket."""
    bucket = by_type_currency.get(instrument_type)
    if bucket is None:
        return
    if currency_upper not in bucket:
        bucket[currency_upper] = []
    if instrument_key not in bucket[currency_upper]:
        bucket[currency_upper].append(instrument_key)


def _find_spot_bid_ask(
    by_type_currency: Dict[str, Dict[str, list[str]]],
    instruments: Dict[str, Dict[str, str]],
    currency: str,
) -> Optional[tuple[float, float]]:
    """Find the first spot instrument with valid bid/ask for the currency."""
    if _SPOT_INSTRUMENT_TYPE not in by_type_currency:
        return None
    spot_bucket = by_type_currency[_SPOT_INSTRUMENT_TYPE]
    currency_upper = currency.upper()
    if currency_upper not in spot_bucket:
        return None
    for key in spot_bucket[currency_upper]:
        if key not in instruments:
            continue
        data = instruments[key]
        bid_str = data.get("best_bid")
        ask_str = data.get("best_ask")
        if bid_str is None or ask_str is None:
            continue
        return float(bid_str), float(ask_str)
    return None


__all__ = ["DeribitInstrumentIndex"]
