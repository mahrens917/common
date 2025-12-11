"""
Orderbook and trade tick write operations.

This module handles writing trade tick data and trade price updates.
"""

import logging
from typing import Any, Dict

from redis.asyncio import Redis

from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable
from .timestamp_normalizer import TimestampNormalizer

logger = logging.getLogger(__name__)


class OrderbookWriter:
    """Handles orderbook and trade tick write operations."""

    def __init__(self, redis_connection: Redis, logger_instance: logging.Logger):
        self.redis = redis_connection
        self.logger = logger_instance
        self._normalizer = TimestampNormalizer()

    async def update_trade_tick(self, msg: Dict, key_func: Any, map_func: Any, str_func: Any) -> bool:
        try:
            data = map_func(msg.get("msg"))
            ticker = data.get("market_ticker")
            if not ticker:
                logger.error("Trade tick missing market_ticker: %s", data)
                return False

            side, yes, no, raw = self._extract_price_data(data, str_func)
            mapping = self._build_trade_mapping(data, side, yes, no, raw)
            await ensure_awaitable(self.redis.hset(key_func(ticker), mapping=mapping))
        except (ValueError, TypeError) as exc:
            logger.error("Invalid trade tick payload: %s", exc, exc_info=True)
            return False
        except REDIS_ERRORS as exc:
            logger.error("Redis error updating trade tick: %s", exc, exc_info=True)
            return False
        else:
            return True

    def _extract_price_data(self, msg: Dict, str_func: Any) -> tuple:
        primary = str_func(msg.get("side")) or str_func(msg.get("taker_side"))
        side = primary.lower()

        yes = msg.get("yes_price")
        no = msg.get("no_price")
        raw = msg.get("price")

        if yes is None and raw is not None:
            yes = self._derive_yes_price_from_raw(raw, side)

        if yes is not None and no is None:
            try:
                no = 100 - float(yes)
            except (TypeError, ValueError):
                no = None
        elif no is not None and yes is None:
            try:
                yes = 100 - float(no)
            except (TypeError, ValueError):
                yes = None

        return side, yes, no, raw

    @staticmethod
    def _derive_yes_price_from_raw(raw: Any, side: str) -> Any:
        try:
            val = float(raw)
        except (TypeError, ValueError):
            return None
        return val if side == "yes" else (100 - val if side == "no" else None)

    def _build_trade_mapping(self, msg: Dict, side: str, yes_price: Any, no_price: Any, raw_price: Any) -> Dict[str, str]:
        ts_value = msg.get("ts") or msg.get("timestamp")
        mapping = _build_trade_base_mapping(
            side,
            msg,
            self._normalizer.normalise_trade_timestamp(ts_value) if ts_value is not None else "",
            ts_value,
        )

        taker = msg.get("taker_side") or msg.get("taker")
        _maybe_set_field(mapping, "last_trade_taker_side", taker)
        _maybe_set_field(mapping, "last_trade_raw_price", raw_price)
        if yes_price is not None:
            _maybe_set_field(mapping, "last_trade_yes_price", yes_price)
            _maybe_set_field(mapping, "last_price", yes_price)
        _maybe_set_field(mapping, "last_trade_no_price", no_price)
        return mapping


def _build_trade_base_mapping(side: str, msg: Dict, ts_iso: str, ts_raw: Any) -> Dict[str, str]:
    """Return the core mapping fields shared by all trade ticks."""
    timestamp_value = ts_iso if ts_iso else (str(ts_raw) if ts_raw not in (None, "") else "")
    count_value = msg.get("count") or msg.get("quantity") or msg.get("size") or ""
    return {
        "last_trade_side": side if side else "",
        "last_trade_count": str(count_value),
        "last_trade_timestamp": timestamp_value,
    }


def _maybe_set_field(mapping: Dict[str, str], field_name: str, value: Any) -> None:
    """Set field on mapping when value is provided."""
    if value is None:
        return
    mapping[field_name] = str(value)
