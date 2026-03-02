"""Deterministic trade hash for dedup across WebSocket and REST API sources."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

_UNIX_MS_THRESHOLD = 9_999_999_999


def ts_to_unix_seconds(ts: str | int | float) -> int:
    """Normalize a timestamp to integer Unix seconds.

    Handles:
    - ISO 8601 strings ("2024-01-15T10:30:00Z") → int(datetime.timestamp())
    - Unix milliseconds (1703721600000) → ts // 1000
    - Unix seconds (1703721600) → int(ts)
    """
    if isinstance(ts, str):
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return int(dt.timestamp())
    numeric = int(ts)
    if numeric > _UNIX_MS_THRESHOLD:
        return numeric // 1000
    return numeric


def make_kalshi_trade_hash(
    ticker: str,
    taker_side: str,
    yes_price: int,
    count: int,
    ts_seconds: int,
) -> str:
    """Compute a deterministic 16-hex-char trade ID from fields shared by both sources.

    Both the analytics batch downloader (REST API) and the kalshi WebSocket writer
    call this with the same inputs for the same trade, producing the same hash.
    ``ON CONFLICT DO NOTHING`` then deduplicates automatically.
    """
    payload = f"{ticker}:{taker_side}:{yes_price}:{count}:{ts_seconds}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
