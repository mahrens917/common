"""Tests for notification helpers."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.order_execution.finalizer_helpers.notification import send_notification
from src.common.trading_exceptions import KalshiTradeNotificationError

FILLED_COUNT_FIVE = 5
REMAINING_COUNT_ZERO = 0


class TestSendNotification:
    """Tests for send_notification function."""

    @pytest.mark.asyncio
    async def test_does_nothing_when_notifier_is_none(self) -> None:
        """Returns early when notifier is None."""
        order_request = MagicMock()
        order_response = MagicMock()

        # Should not raise
        await send_notification(
            None, order_request, order_response, "order-123", MagicMock(), "test_op"
        )

    @pytest.mark.asyncio
    async def test_sends_notification_to_notifier(self) -> None:
        """Sends notification when notifier is provided."""
        notifier = AsyncMock()
        notifier.send_order_executed_notification = AsyncMock()

        order_request = MagicMock()
        order_request.ticker = "TICKER-123"
        order_request.action.value = "buy"
        order_request.side.value = "yes"
        order_request.yes_price_cents = 50

        order_response = MagicMock()
        order_response.order_id = "order-123"
        order_response.filled_count = FILLED_COUNT_FIVE
        order_response.remaining_count = REMAINING_COUNT_ZERO
        order_response.client_order_id = "client-123"
        order_response.status.value = "filled"
        order_response.average_fill_price_cents = 50
        order_response.fees_cents = 2

        kalshi_client = MagicMock()

        with (
            patch(
                "src.common.order_execution.finalizer_helpers.notification.build_order_data_payload",
                return_value={"ticker": "TICKER-123"},
            ),
            patch(
                "src.common.order_execution.finalizer_helpers.notification.build_response_data_payload",
                return_value={"order_id": "order-123"},
            ),
        ):
            await send_notification(
                notifier,
                order_request,
                order_response,
                "order-123",
                kalshi_client,
                "test_op",
            )

        notifier.send_order_executed_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_notification_error_on_runtime_error(self) -> None:
        """Raises KalshiTradeNotificationError on RuntimeError."""
        notifier = AsyncMock()
        notifier.send_order_executed_notification = AsyncMock(
            side_effect=RuntimeError("Connection failed")
        )

        order_request = MagicMock()
        order_response = MagicMock()
        order_response.filled_count = FILLED_COUNT_FIVE
        order_response.remaining_count = REMAINING_COUNT_ZERO

        with (
            patch(
                "src.common.order_execution.finalizer_helpers.notification.build_order_data_payload",
                return_value={},
            ),
            patch(
                "src.common.order_execution.finalizer_helpers.notification.build_response_data_payload",
                return_value={},
            ),
        ):
            with pytest.raises(KalshiTradeNotificationError):
                await send_notification(
                    notifier,
                    order_request,
                    order_response,
                    "order-123",
                    MagicMock(),
                    "test_op",
                )

    @pytest.mark.asyncio
    async def test_raises_notification_error_on_timeout(self) -> None:
        """Raises KalshiTradeNotificationError on timeout."""
        notifier = AsyncMock()
        notifier.send_order_executed_notification = AsyncMock(side_effect=asyncio.TimeoutError())

        order_request = MagicMock()
        order_response = MagicMock()
        order_response.filled_count = FILLED_COUNT_FIVE
        order_response.remaining_count = REMAINING_COUNT_ZERO

        with (
            patch(
                "src.common.order_execution.finalizer_helpers.notification.build_order_data_payload",
                return_value={},
            ),
            patch(
                "src.common.order_execution.finalizer_helpers.notification.build_response_data_payload",
                return_value={},
            ),
        ):
            with pytest.raises(KalshiTradeNotificationError):
                await send_notification(
                    notifier,
                    order_request,
                    order_response,
                    "order-456",
                    MagicMock(),
                    "test_op",
                )

    @pytest.mark.asyncio
    async def test_raises_notification_error_on_connection_error(self) -> None:
        """Raises KalshiTradeNotificationError on ConnectionError."""
        notifier = AsyncMock()
        notifier.send_order_executed_notification = AsyncMock(
            side_effect=ConnectionError("Network error")
        )

        order_request = MagicMock()
        order_response = MagicMock()
        order_response.filled_count = FILLED_COUNT_FIVE
        order_response.remaining_count = REMAINING_COUNT_ZERO

        with (
            patch(
                "src.common.order_execution.finalizer_helpers.notification.build_order_data_payload",
                return_value={},
            ),
            patch(
                "src.common.order_execution.finalizer_helpers.notification.build_response_data_payload",
                return_value={},
            ),
        ):
            with pytest.raises(KalshiTradeNotificationError):
                await send_notification(
                    notifier,
                    order_request,
                    order_response,
                    "order-789",
                    MagicMock(),
                    "test_op",
                )
