"""Orderbook message dispatcher."""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict

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
