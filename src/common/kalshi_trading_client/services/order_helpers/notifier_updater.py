"""Helper for updating OrderService notifier and telegram handler."""

from typing import Any


def update_order_notifier(order_creator: Any, notifier: Any) -> None:
    """Update the notifier in order creator."""
    order_creator._notifier = notifier


def update_metadata_telegram_handler(metadata_ops: Any, handler: Any) -> None:
    """Update the telegram handler in metadata operations."""
    metadata_ops.update_telegram_handler(handler)


def has_sufficient_balance_for_trade_with_fees(
    bal_cents: int, cost_cents: int, fees_cents: int
) -> bool:
    """Check if balance is sufficient for trade with fees."""
    from .order_service_operations import ValidationOperations

    return ValidationOperations.has_sufficient_balance_for_trade_with_fees(
        bal_cents, cost_cents, fees_cents
    )
