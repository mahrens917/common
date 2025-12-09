from __future__ import annotations

"""Order metadata helpers for the Kalshi trading workflow."""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional, Protocol, Tuple

try:
    from src.monitor.alerter import ALERT_FAILURE_ERRORS as _ALERTER_FAILURES
except ModuleNotFoundError:
    _ALERTER_FAILURES = ()

from ..data_models.trade_record import is_trade_reason_valid
from ..trading_exceptions import KalshiDataIntegrityError

ALERT_SEND_ERRORS = _ALERTER_FAILURES + (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    RuntimeError,
    ValueError,
)


class AlertSender(Protocol):
    async def send_alert(self, message: str) -> None: ...


async def fetch_order_metadata(
    order_id: str,
    trade_store_supplier: Callable[[], Awaitable[Any]],
    telegram_handler: Optional[AlertSender],
    logger: logging.Logger,
) -> Tuple[str, str]:
    """Retrieve the trade rule and reason for the given order id."""

    trade_store = await trade_store_supplier()
    metadata = await trade_store.get_order_metadata(order_id)

    if metadata and metadata.get("trade_rule") and metadata.get("trade_reason"):
        trade_rule = metadata["trade_rule"]
        trade_reason = metadata["trade_reason"]

        if is_trade_reason_valid(trade_reason):
            return trade_reason, trade_rule
        raise ValueError(f"Trade reason too short: {trade_reason}")

    error_msg = (
        f"CRITICAL: No order metadata found for order {order_id}. "
        "Metadata persistence is required for every order."
    )
    logger.error(error_msg)

    if telegram_handler:
        try:
            await telegram_handler.send_alert(
                f"🚨 ORDER METADATA MISSING\n\n{error_msg}\n\nImmediate investigation required."
            )
        except ALERT_SEND_ERRORS as alert_exc:
            logger.warning(
                "Failed to send missing metadata alert for order %s: %s",
                order_id,
                alert_exc,
            )

    raise KalshiDataIntegrityError(error_msg)
