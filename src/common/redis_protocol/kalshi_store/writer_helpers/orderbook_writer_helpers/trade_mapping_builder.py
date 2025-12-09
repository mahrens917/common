"""Build trade tick mapping for Redis storage."""

from typing import Any, Dict


def build_trade_tick_mapping(
    msg: Dict, side: str, yes_price: Any, no_price: Any, raw_price: Any, timestamp_normalizer: Any
) -> Dict[str, str]:
    """
    Build Redis mapping dictionary for trade tick data.

    Args:
        msg: Trade tick message
        side: Trade side
        yes_price: Yes price
        no_price: No price
        raw_price: Raw price
        timestamp_normalizer: Timestamp normalizer

    Returns:
        Mapping dictionary for Redis HSET
    """
    ts = msg.get("ts") or msg.get("timestamp")
    ts_iso = timestamp_normalizer.normalise_trade_timestamp(ts) if ts is not None else ""

    mapping = _build_base_mapping(msg, side, ts, ts_iso)
    _add_taker_side(mapping, msg)
    _add_prices(mapping, yes_price, no_price, raw_price)

    return mapping


def _build_base_mapping(msg: Dict, side: str, ts: Any, ts_iso: str) -> Dict[str, str]:
    """Build base mapping with required fields."""
    return {
        "last_trade_side": side if side else "",
        "last_trade_count": str(msg.get("count") or msg.get("quantity") or msg.get("size") or ""),
        "last_trade_timestamp": ts_iso if ts_iso else (str(ts) if ts not in (None, "") else ""),
    }


def _add_taker_side(mapping: Dict[str, str], msg: Dict) -> None:
    """Add taker side to mapping if available."""
    taker = msg.get("taker_side") or msg.get("taker")
    if taker:
        mapping["last_trade_taker_side"] = str(taker)


def _add_prices(mapping: Dict[str, str], yes_price: Any, no_price: Any, raw_price: Any) -> None:
    """Add price fields to mapping."""
    if raw_price is not None:
        mapping["last_trade_raw_price"] = str(raw_price)
    if yes_price is not None:
        mapping["last_trade_yes_price"] = str(yes_price)
        mapping["last_price"] = str(yes_price)
    if no_price is not None:
        mapping["last_trade_no_price"] = str(no_price)
