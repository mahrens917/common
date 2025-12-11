from __future__ import annotations

"""Attribute update handler for notifier and telegram handler sync."""


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..services import OrderService


class AttributeHandler:
    """Handles attribute updates that need to sync with services."""

    @staticmethod
    def handle_notifier_update(orders_service: OrderService | None, notifier) -> None:
        """Update notifier in orders service."""
        if orders_service is not None:
            orders_service.update_notifier(notifier)

    @staticmethod
    def handle_telegram_handler_update(orders_service: OrderService | None, telegram_handler) -> None:
        """Update telegram handler in orders service."""
        if orders_service is not None:
            orders_service.update_telegram_handler(telegram_handler)
