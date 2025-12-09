"""Utility functions for trade record operations."""

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..trade_record import TradeRecord

ALLOWED_SHORT_TRADE_REASONS = {"storm", "rebalance"}


# Constants
_CONST_10 = 10


def is_trade_reason_valid(reason: str) -> bool:
    """Return True when the trade reason meets minimum descriptive requirements."""

    normalized = reason.strip().lower()
    if not normalized:
        return False
    if len(normalized) >= _CONST_10:
        return True
    return normalized in ALLOWED_SHORT_TRADE_REASONS


def get_trade_close_date(trade: "TradeRecord") -> date:
    """Return the effective close date for a trade."""

    if trade.settlement_time is not None:
        return trade.settlement_time.date()
    return trade.trade_timestamp.date()
