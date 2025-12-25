"""Storage helpers for TradeFinalizer."""

import logging

from ...redis_protocol.trade_store import TradeStore, TradeStoreError
from ...trading_exceptions import KalshiTradePersistenceError
from ..polling import PollingOutcome

logger = logging.getLogger(__name__)


async def store_trade_record(
    trade_store: TradeStore,
    trade_record,
    order_id: str,
    outcome: PollingOutcome,
    operation_name: str,
) -> None:
    """Store trade record in trade store."""
    try:
        await trade_store.store_trade(trade_record)
        logger.info(
            "[%s] Stored trade immediately in trade store: order_id=%s quantity=%s",
            operation_name,
            order_id,
            outcome.total_filled,
        )
    except TradeStoreError as exc:
        raise KalshiTradePersistenceError(
            f"Failed to store trade",
            order_id=order_id,
            ticker=trade_record.ticker,
            operation_name=operation_name,
        ) from exc
