"""Tests for notifier_adapter module."""

import asyncio
import urllib.error
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from common.data_models.trading import OrderAction, OrderRequest, OrderSide, OrderType
from common.trading.notifier_adapter import TradeNotifierAdapter
from common.trading_exceptions import KalshiTradeNotificationError


def _build_order_request() -> OrderRequest:
    """Build a test order request."""
    return OrderRequest(
        ticker="TEST-25JAN01",
        action=OrderAction.BUY,
        side=OrderSide.YES,
        count=1,
        client_order_id="test-order-id",
        trade_rule="test_rule",
        trade_reason="Test reason for testing",
        order_type=OrderType.LIMIT,
        yes_price_cents=50,
    )


class TestTradeNotifierAdapterInit:
    """Tests for TradeNotifierAdapter initialization."""

    def test_initializes_with_custom_supplier(self) -> None:
        """Initializes with custom notifier supplier."""
        supplier = Mock()
        error_types = (RuntimeError,)

        adapter = TradeNotifierAdapter(
            notifier_supplier=supplier,
            notification_error_types=error_types,
        )

        assert adapter._notifier_supplier is supplier
        assert adapter._notification_error_types == error_types

    def test_handles_import_error_gracefully(self, monkeypatch) -> None:
        """Handles ImportError when trade_notifier is unavailable."""

        def raise_import_error(*args, **kwargs):
            raise ImportError("Module not found")

        monkeypatch.setattr("builtins.__import__", raise_import_error)

        adapter = TradeNotifierAdapter()

        assert adapter._notifier_supplier is None
        assert adapter._notification_error_types == ()


class FakeTradeNotificationError(Exception):
    """Fake TradeNotificationError for testing."""


class TestNotifyOrderError:
    """Tests for notify_order_error method."""

    @pytest.mark.asyncio
    async def test_uses_imported_error_type_when_available(self, monkeypatch) -> None:
        """Uses imported TradeNotificationError when available."""
        import builtins
        import sys

        # Create a fake module
        class FakeModule:
            TradeNotificationError = FakeTradeNotificationError

        # Patch import to return our fake module
        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "kalshi.notifications.trade_notifier":
                return FakeModule()
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", custom_import)

        notifier = MagicMock()
        notifier.send_order_error_notification = AsyncMock(side_effect=FakeTradeNotificationError("Test"))

        adapter = TradeNotifierAdapter(
            notifier_supplier=lambda: notifier,
            notification_error_types=(),
        )
        order_request = _build_order_request()
        error = ValueError("Test error")

        with pytest.raises(KalshiTradeNotificationError, match="Test message"):
            await adapter.notify_order_error(
                order_request,
                error,
                operation_name="test_op",
                notifier_error_message="Test message",
            )

    @pytest.mark.asyncio
    async def test_raises_when_supplier_raises_runtime_error(self) -> None:
        """Raises KalshiTradeNotificationError when supplier raises RuntimeError."""

        def raise_error():
            raise RuntimeError("Notifier unavailable")

        adapter = TradeNotifierAdapter(notifier_supplier=raise_error)
        order_request = _build_order_request()
        error = ValueError("Test error")

        with pytest.raises(KalshiTradeNotificationError, match="Trade notifier unavailable"):
            await adapter.notify_order_error(
                order_request,
                error,
                operation_name="test_op",
                notifier_error_message="Test message",
            )

    @pytest.mark.asyncio
    async def test_returns_early_when_notifier_is_none(self) -> None:
        """Returns early when notifier is None."""
        adapter = TradeNotifierAdapter(notifier_supplier=lambda: None)
        order_request = _build_order_request()
        error = ValueError("Test error")

        await adapter.notify_order_error(
            order_request,
            error,
            operation_name="test_op",
            notifier_error_message="Test message",
        )

    @pytest.mark.asyncio
    async def test_handles_import_error_for_error_types(self, monkeypatch) -> None:
        """Handles ImportError when getting error types."""
        import builtins

        notifier = MagicMock()
        notifier.send_order_error_notification = AsyncMock(side_effect=RuntimeError("Test"))

        # Create adapter with empty error types to trigger dynamic import
        adapter = TradeNotifierAdapter(
            notifier_supplier=lambda: notifier,
            notification_error_types=(),
        )

        # Patch the import inside notify_order_error to raise ImportError
        original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if name == "kalshi.notifications.trade_notifier":
                raise ImportError("Module not found")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", custom_import)

        order_request = _build_order_request()
        error = ValueError("Test error")

        # The error is caught by the imported RuntimeError type after ImportError
        with pytest.raises(KalshiTradeNotificationError, match="Test message"):
            await adapter.notify_order_error(
                order_request,
                error,
                operation_name="test_op",
                notifier_error_message="Test message",
            )

    @pytest.mark.asyncio
    async def test_raises_on_connection_error(self) -> None:
        """Raises KalshiTradeNotificationError on ConnectionError."""
        notifier = MagicMock()
        notifier.send_order_error_notification = AsyncMock(side_effect=ConnectionError("Network down"))

        adapter = TradeNotifierAdapter(
            notifier_supplier=lambda: notifier,
            notification_error_types=(ValueError,),
        )
        order_request = _build_order_request()
        error = ValueError("Test error")

        with pytest.raises(KalshiTradeNotificationError, match="Trade notifier unavailable"):
            await adapter.notify_order_error(
                order_request,
                error,
                operation_name="test_op",
                notifier_error_message="Test message",
            )

    @pytest.mark.asyncio
    async def test_raises_on_timeout_error(self) -> None:
        """Raises KalshiTradeNotificationError on TimeoutError."""
        notifier = MagicMock()
        notifier.send_order_error_notification = AsyncMock(side_effect=TimeoutError("Timeout"))

        adapter = TradeNotifierAdapter(
            notifier_supplier=lambda: notifier,
            notification_error_types=(ValueError,),
        )
        order_request = _build_order_request()
        error = ValueError("Test error")

        with pytest.raises(KalshiTradeNotificationError, match="Trade notifier unavailable"):
            await adapter.notify_order_error(
                order_request,
                error,
                operation_name="test_op",
                notifier_error_message="Test message",
            )

    @pytest.mark.asyncio
    async def test_raises_on_asyncio_timeout_error(self) -> None:
        """Raises KalshiTradeNotificationError on asyncio.TimeoutError."""
        notifier = MagicMock()
        notifier.send_order_error_notification = AsyncMock(side_effect=asyncio.TimeoutError("Async timeout"))

        adapter = TradeNotifierAdapter(
            notifier_supplier=lambda: notifier,
            notification_error_types=(ValueError,),
        )
        order_request = _build_order_request()
        error = ValueError("Test error")

        with pytest.raises(KalshiTradeNotificationError, match="Trade notifier unavailable"):
            await adapter.notify_order_error(
                order_request,
                error,
                operation_name="test_op",
                notifier_error_message="Test message",
            )

    @pytest.mark.asyncio
    async def test_raises_on_urllib_error(self) -> None:
        """Raises KalshiTradeNotificationError on urllib.error.URLError."""
        notifier = MagicMock()
        notifier.send_order_error_notification = AsyncMock(side_effect=urllib.error.URLError("URL error"))

        adapter = TradeNotifierAdapter(
            notifier_supplier=lambda: notifier,
            notification_error_types=(ValueError,),
        )
        order_request = _build_order_request()
        error = ValueError("Test error")

        with pytest.raises(KalshiTradeNotificationError, match="Trade notifier unavailable"):
            await adapter.notify_order_error(
                order_request,
                error,
                operation_name="test_op",
                notifier_error_message="Test message",
            )
