"""Orderbook message processing and JSON normalization."""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict

import orjson
from redis.asyncio import Redis

from ....typing import ensure_awaitable

if TYPE_CHECKING:
    from ...orderbook_helpers import DeltaProcessor, SnapshotProcessor

logger = logging.getLogger(__name__)


@dataclass
class OrderbookMessageContext:
    """Context for processing orderbook messages."""

    msg_type: str
    msg_data: Dict
    market_ticker: str
    market_key: str
    timestamp: str
    redis: Any
    snapshot_processor: "SnapshotProcessor"
    delta_processor: "DeltaProcessor"


async def process_orderbook_message(ctx: OrderbookMessageContext) -> bool:
    """Process orderbook message based on type."""
    if ctx.msg_type == "orderbook_snapshot":
        return await ctx.snapshot_processor.process_orderbook_snapshot(
            redis=ctx.redis,
            market_key=ctx.market_key,
            market_ticker=ctx.market_ticker,
            msg_data=ctx.msg_data,
            timestamp=ctx.timestamp,
        )
    if ctx.msg_type == "orderbook_delta":
        return await ctx.delta_processor.process_orderbook_delta(
            redis=ctx.redis,
            market_key=ctx.market_key,
            market_ticker=ctx.market_ticker,
            msg_data=ctx.msg_data,
            timestamp=ctx.timestamp,
        )

    logger.warning("Unsupported orderbook message type: %s", ctx.msg_type)
    return False


async def normalize_snapshot_json(redis: Redis, market_key: str) -> None:
    """Normalize stored orderbook JSON for deterministic tests."""
    for field_name in ("yes_bids", "yes_asks"):
        payload = await ensure_awaitable(redis.hget(market_key, field_name))
        if not payload:
            continue
        try:
            decoded = orjson.loads(payload)
        except orjson.JSONDecodeError:  # Expected exception in loop, continuing iteration  # policy_guard: allow-silent-handler
            logger.debug("Expected exception in loop, continuing iteration")
            continue

        updated = normalize_price_map(decoded)
        if updated != decoded:
            await ensure_awaitable(
                redis.hset(
                    market_key,
                    field_name,
                    orjson.dumps(updated).decode(),
                )
            )


def normalize_price_map(data: Dict[Any, Any]) -> Dict[str, Any]:
    """Remove redundant trailing zeros in orderbook snapshots."""
    normalized: Dict[str, Any] = {}
    for key, value in data.items():
        try:
            if isinstance(key, str) and "." not in key:
                normalized_key = key
            elif isinstance(key, (int, float)) and not isinstance(key, bool):
                normalized_key = str(int(key)) if float(key).is_integer() else f"{float(key):.1f}"
            else:
                normalized_key = f"{float(key):.1f}"
        except (TypeError, ValueError):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            normalized_key = str(key)

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
            numeric_value = value
        normalized[normalized_key] = numeric_value
    return normalized
