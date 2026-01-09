"""
Orderbook and trade tick write operations.

This module handles writing trade tick data and trade price updates.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from redis.asyncio import Redis

from common.redis_schema import build_kalshi_market_key
from common.truthy import pick_if, pick_truthy

from ...error_types import REDIS_ERRORS
from ...typing import ensure_awaitable
from .market_update_writer import RedisConnectionMixin
from .timestamp_normalizer import TimestampNormalizer

if TYPE_CHECKING:
    from ..connection import RedisConnectionManager

logger = logging.getLogger(__name__)

# Sentinel value for unspecified/missing side data (causes validation error)
SIDE_UNSPECIFIED = ""

# Empty string constant for algo field when not set
_NO_ALGO = str()


class OrderbookWriter(RedisConnectionMixin):
    """Handles orderbook and trade tick write operations."""

    def __init__(
        self,
        redis_connection: Optional[Redis],
        logger_instance: logging.Logger,
        connection_manager: Optional["RedisConnectionManager"] = None,
    ):
        self.redis = redis_connection
        self.logger = logger_instance
        self._connection_manager = connection_manager
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
            redis_client = await self._ensure_redis()
            await ensure_awaitable(redis_client.hset(key_func(ticker), mapping=mapping))
        except (ValueError, TypeError) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            logger.error("Invalid trade tick payload: %s", exc, exc_info=True)
            return False
        except REDIS_ERRORS as exc:  # Expected exception, returning default value  # policy_guard: allow-silent-handler
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
            except (TypeError, ValueError):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
                no = None
        elif no is not None and yes is None:
            try:
                yes = 100 - float(no)
            except (TypeError, ValueError):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
                yes = None

        return side, yes, no, raw

    @staticmethod
    def _derive_yes_price_from_raw(raw: Any, side: str) -> Any:
        try:
            val = float(raw)
        except (TypeError, ValueError) as exc:  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            logger.warning("Failed to parse raw price as float: raw=%r, side=%r, error=%s", raw, side, exc)
            return None
        return val if side == "yes" else (100 - val if side == "no" else None)

    def _build_trade_mapping(self, msg: Dict, side: str, yes_price: Any, no_price: Any, raw_price: Any) -> Dict[str, str]:
        ts_value = msg.get("ts") or msg.get("timestamp")
        mapping = _build_trade_base_mapping(
            side,
            msg,
            pick_if(ts_value is not None, lambda: self._normalizer.normalise_trade_timestamp(ts_value), lambda: ""),
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
    timestamp_value = ts_iso if ts_iso else pick_if(ts_raw not in (None, ""), lambda: str(ts_raw), lambda: "")
    count_value = pick_truthy(msg.get("count") or msg.get("quantity") or msg.get("size"), "")
    return {
        "last_trade_side": pick_if(side, lambda: side, lambda: ""),
        "last_trade_count": str(count_value),
        "last_trade_timestamp": timestamp_value,
    }


def _maybe_set_field(mapping: Dict[str, str], field_name: str, value: Any) -> None:
    """Set field on mapping when value is provided."""
    if value is None:
        return
    mapping[field_name] = str(value)


def _resolve_fill_price(data: Dict) -> int:
    """Resolve fill price from yes_price based on side.

    Kalshi fill messages contain yes_price which is the YES side price.
    For YES fills, we use yes_price directly.
    For NO fills, we calculate 100 - yes_price.
    """
    yes_price = data.get("yes_price")
    if yes_price is None:
        raise ValueError("Fill missing yes_price field")
    try:
        yes_price_int = int(yes_price)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid yes_price value: {yes_price}") from exc

    side_raw = data.get("side")
    side = str(side_raw).lower() if side_raw is not None else SIDE_UNSPECIFIED
    if side == "yes":
        return yes_price_int
    if side == "no":
        return 100 - yes_price_int
    raise ValueError(f"Invalid fill side: {side}")


def _build_fill_mapping(data: Dict, fill_price: int, ts_iso: str, algo: str) -> Dict[str, str]:
    """Build mapping dictionary for user fill."""
    return {
        "ticker": str(data.get("ticker")),
        "side": str(pick_truthy(data.get("side"), "")),
        "action": str(pick_truthy(data.get("action"), "")),
        "count": str(pick_truthy(data.get("count"), 0)),
        "price": str(fill_price),
        "trade_id": str(data.get("trade_id")),
        "ts": ts_iso,
        "algo": algo,
    }


def _build_order_mapping(data: Dict, ts_iso: str) -> Dict[str, str]:
    """Build mapping dictionary for user order."""
    return {
        "ticker": str(data.get("ticker")),
        "order_id": str(data.get("order_id")),
        "status": str(pick_truthy(data.get("status"), "")),
        "action": str(pick_truthy(data.get("action"), "")),
        "side": str(pick_truthy(data.get("side"), "")),
        "type": str(pick_truthy(data.get("type"), "")),
        "count": str(pick_truthy(data.get("count"), 0)),
        "remaining_count": str(pick_truthy(data.get("remaining_count"), 0)),
        "price": str(pick_truthy(data.get("price"), 0)),
        "ts": ts_iso,
    }


class UserDataWriter(RedisConnectionMixin):
    """Handles user fill and order write operations."""

    def __init__(
        self,
        redis_connection: Optional[Redis],
        logger_instance: logging.Logger,
        connection_manager: Optional["RedisConnectionManager"] = None,
    ):
        self.redis = redis_connection
        self.logger = logger_instance
        self._connection_manager = connection_manager
        self._normalizer = TimestampNormalizer()

    async def _fetch_market_algo(self, ticker: str) -> str:
        """Fetch the current algo from the market's Redis hash."""
        market_key = build_kalshi_market_key(ticker)
        try:
            redis_client = await self._ensure_redis()
            algo = await ensure_awaitable(redis_client.hget(market_key, "algo"))
            if algo is None:
                return _NO_ALGO
            return algo.decode("utf-8") if isinstance(algo, bytes) else str(algo)
        except REDIS_ERRORS:  # policy_guard: allow-silent-handler
            logger.debug("Failed to fetch algo for %s", ticker)
            return _NO_ALGO

    async def update_user_fill(self, msg: Dict) -> bool:
        """Persist a user fill notification to Redis."""
        try:
            inner_msg = msg.get("msg")
            data = inner_msg if isinstance(inner_msg, dict) else msg
            ticker, trade_id = data.get("ticker"), data.get("trade_id")
            if not ticker or not trade_id:
                logger.error("User fill missing ticker or trade_id: %s", data)
                return False

            ts_value = data.get("ts")
            ts_iso = pick_if(ts_value, lambda: self._normalizer.normalise_trade_timestamp(ts_value), lambda: "")
            mapping = _build_fill_mapping(data, _resolve_fill_price(data), ts_iso, await self._fetch_market_algo(str(ticker)))

            redis_client = await self._ensure_redis()
            await ensure_awaitable(redis_client.hset(f"kalshi:fills:{ticker}:{trade_id}", mapping=mapping))
            await ensure_awaitable(redis_client.lpush(f"kalshi:fills:{ticker}", trade_id))
            await ensure_awaitable(redis_client.ltrim(f"kalshi:fills:{ticker}", 0, 99))
        except (ValueError, TypeError) as exc:  # policy_guard: allow-silent-handler
            logger.error("Invalid user fill payload: %s", exc, exc_info=True)
            return False
        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.error("Redis error updating user fill: %s", exc, exc_info=True)
            return False
        else:
            return True

    async def update_user_order(self, msg: Dict) -> bool:
        """Persist a user order notification to Redis."""
        try:
            inner_msg = msg.get("msg")
            data = inner_msg if isinstance(inner_msg, dict) else msg
            ticker, order_id = data.get("ticker"), data.get("order_id")
            if not ticker or not order_id:
                logger.error("User order missing ticker or order_id: %s", data)
                return False

            ts_value = data.get("ts")
            ts_iso = pick_if(ts_value, lambda: self._normalizer.normalise_trade_timestamp(ts_value), lambda: "")
            mapping = _build_order_mapping(data, ts_iso)

            redis_client = await self._ensure_redis()
            await ensure_awaitable(redis_client.hset(f"kalshi:orders:{ticker}:{order_id}", mapping=mapping))
        except (ValueError, TypeError) as exc:  # policy_guard: allow-silent-handler
            logger.error("Invalid user order payload: %s", exc, exc_info=True)
            return False
        except REDIS_ERRORS as exc:  # policy_guard: allow-silent-handler
            logger.error("Redis error updating user order: %s", exc, exc_info=True)
            return False
        else:
            return True
