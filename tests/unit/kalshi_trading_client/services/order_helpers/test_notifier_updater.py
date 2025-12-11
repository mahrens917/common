"""Tests for notifier updater."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from common.kalshi_trading_client.services.order_helpers.notifier_updater import (
    has_sufficient_balance_for_trade_with_fees,
    update_metadata_telegram_handler,
    update_order_notifier,
)


class TestUpdateOrderNotifier:
    """Tests for update_order_notifier function."""

    def test_sets_notifier_on_order_creator(self) -> None:
        """Sets _notifier attribute on order_creator."""
        order_creator = MagicMock()
        notifier = MagicMock()

        update_order_notifier(order_creator, notifier)

        assert order_creator._notifier is notifier

    def test_replaces_existing_notifier(self) -> None:
        """Replaces existing notifier."""
        order_creator = MagicMock()
        old_notifier = MagicMock()
        new_notifier = MagicMock()
        order_creator._notifier = old_notifier

        update_order_notifier(order_creator, new_notifier)

        assert order_creator._notifier is new_notifier
        assert order_creator._notifier is not old_notifier


class TestUpdateMetadataTelegramHandler:
    """Tests for update_metadata_telegram_handler function."""

    def test_calls_update_telegram_handler(self) -> None:
        """Calls update_telegram_handler on metadata_ops."""
        metadata_ops = MagicMock()
        handler = MagicMock()

        update_metadata_telegram_handler(metadata_ops, handler)

        metadata_ops.update_telegram_handler.assert_called_once_with(handler)


class TestHasSufficientBalanceForTradeWithFees:
    """Tests for has_sufficient_balance_for_trade_with_fees function."""

    def test_delegates_to_validation_operations(self) -> None:
        """Delegates to ValidationOperations."""
        with patch("common.kalshi_trading_client.services.order_helpers.order_service_operations.ValidationOperations") as mock_ops:
            mock_ops.has_sufficient_balance_for_trade_with_fees.return_value = True

            result = has_sufficient_balance_for_trade_with_fees(bal_cents=1000, cost_cents=500, fees_cents=50)

            mock_ops.has_sufficient_balance_for_trade_with_fees.assert_called_once_with(1000, 500, 50)
            assert result is True

    def test_returns_false_when_insufficient(self) -> None:
        """Returns False when balance is insufficient."""
        with patch("common.kalshi_trading_client.services.order_helpers.order_service_operations.ValidationOperations") as mock_ops:
            mock_ops.has_sufficient_balance_for_trade_with_fees.return_value = False

            result = has_sufficient_balance_for_trade_with_fees(bal_cents=100, cost_cents=500, fees_cents=50)

            assert result is False
