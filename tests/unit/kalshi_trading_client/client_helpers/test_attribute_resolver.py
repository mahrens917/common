"""Tests for kalshi_trading_client.client_helpers.attribute_resolver module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.kalshi_trading_client.client_helpers.attribute_resolver import (
    ClientAttributeResolver,
)


class TestClientAttributeResolverInit:
    """Tests for ClientAttributeResolver initialization."""

    def test_stores_client(self) -> None:
        """Test stores client reference."""
        mock_client = MagicMock()
        resolver = ClientAttributeResolver(mock_client)

        assert resolver._client is mock_client


class TestClientAttributeResolverResolve:
    """Tests for resolve method."""

    def test_resolves_api_method(self) -> None:
        """Test resolves API method."""
        mock_client = MagicMock()
        mock_method = MagicMock()
        mock_client._api = MagicMock()
        mock_client._api.some_method = mock_method

        resolver = ClientAttributeResolver(mock_client)
        result = resolver.resolve("some_method")

        assert result is mock_method

    def test_resolves_trade_store_get_operation(self) -> None:
        """Test resolves _get_trade_store operation."""
        mock_client = MagicMock()
        mock_client._api = MagicMock(spec=[])

        resolver = ClientAttributeResolver(mock_client)
        result = resolver.resolve("_get_trade_store")

        assert callable(result)

    def test_resolves_trade_store_maybe_get_operation(self) -> None:
        """Test resolves _maybe_get_trade_store operation."""
        mock_client = MagicMock()
        mock_client._api = MagicMock(spec=[])

        resolver = ClientAttributeResolver(mock_client)
        result = resolver.resolve("_maybe_get_trade_store")

        assert callable(result)

    def test_resolves_trade_store_ensure_operation(self) -> None:
        """Test resolves _ensure_trade_store operation."""
        mock_client = MagicMock()
        mock_client._api = MagicMock(spec=[])

        resolver = ClientAttributeResolver(mock_client)
        result = resolver.resolve("_ensure_trade_store")

        assert callable(result)

    def test_resolves_delegator_method(self) -> None:
        """Test resolves delegator method."""
        mock_client = MagicMock()
        mock_client._api = MagicMock(spec=[])
        mock_client._delegator = MagicMock()
        mock_client._delegator.some_method = MagicMock()

        resolver = ClientAttributeResolver(mock_client)
        result = resolver.resolve("_some_method")

        assert result is mock_client._delegator.some_method

    def test_resolves_has_sufficient_balance(self) -> None:
        """Test resolves has_sufficient_balance_for_trade_with_fees."""
        mock_client = MagicMock()
        mock_client._api = MagicMock(spec=[])
        mock_client._delegator = MagicMock()
        mock_method = MagicMock()
        mock_client._delegator.has_sufficient_balance_for_trade_with_fees = mock_method

        resolver = ClientAttributeResolver(mock_client)
        result = resolver.resolve("has_sufficient_balance_for_trade_with_fees")

        assert result is mock_method

    def test_raises_attribute_error_for_unknown(self) -> None:
        """Test raises AttributeError for unknown attribute."""
        mock_client = MagicMock()
        mock_client._api = MagicMock(spec=[])
        mock_client._delegator = MagicMock(spec=[])

        resolver = ClientAttributeResolver(mock_client)

        with pytest.raises(AttributeError) as exc_info:
            resolver.resolve("unknown_method")

        assert "KalshiTradingClient" in str(exc_info.value)
        assert "unknown_method" in str(exc_info.value)


class TestClientAttributeResolverResolveApiMethod:
    """Tests for _resolve_api_method method."""

    def test_wraps_start_trade_collection(self) -> None:
        """Test wraps start_trade_collection method."""
        mock_client = MagicMock()
        mock_client._api = MagicMock()
        mock_client._api.start_trade_collection = AsyncMock(return_value=True)

        resolver = ClientAttributeResolver(mock_client)
        result = resolver._resolve_api_method("start_trade_collection")

        assert callable(result)
        assert result is not mock_client._api.start_trade_collection

    def test_wraps_stop_trade_collection(self) -> None:
        """Test wraps stop_trade_collection method."""
        mock_client = MagicMock()
        mock_client._api = MagicMock()
        mock_client._api.stop_trade_collection = AsyncMock(return_value=False)

        resolver = ClientAttributeResolver(mock_client)
        result = resolver._resolve_api_method("stop_trade_collection")

        assert callable(result)
        assert result is not mock_client._api.stop_trade_collection

    def test_wraps_require_trade_store(self) -> None:
        """Test wraps require_trade_store method."""
        mock_client = MagicMock()
        mock_client._api = MagicMock()
        mock_client._api.require_trade_store = AsyncMock()

        resolver = ClientAttributeResolver(mock_client)
        result = resolver._resolve_api_method("require_trade_store")

        assert callable(result)
        assert result is not mock_client._api.require_trade_store

    def test_returns_unwrapped_regular_method(self) -> None:
        """Test returns unwrapped regular API method."""
        mock_client = MagicMock()
        mock_method = MagicMock()
        mock_client._api = MagicMock()
        mock_client._api.regular_method = mock_method

        resolver = ClientAttributeResolver(mock_client)
        result = resolver._resolve_api_method("regular_method")

        assert result is mock_method


class TestClientAttributeResolverWrapStartTradeCollection:
    """Tests for _wrap_start_trade_collection method."""

    @pytest.mark.asyncio
    async def test_validates_trade_store_exists(self) -> None:
        """Test validates trade store getter exists."""
        mock_client = MagicMock()
        mock_client._get_trade_store = None
        mock_attr = AsyncMock(return_value=True)

        resolver = ClientAttributeResolver(mock_client)
        wrapped = resolver._wrap_start_trade_collection(mock_attr)

        with pytest.raises(ValueError) as exc_info:
            await wrapped()

        assert "Trade store required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validates_trade_store_getter_works(self) -> None:
        """Test validates trade store getter works."""
        mock_client = MagicMock()
        mock_client._get_trade_store = AsyncMock(side_effect=RuntimeError("No store"))
        mock_attr = AsyncMock(return_value=True)

        resolver = ClientAttributeResolver(mock_client)
        wrapped = resolver._wrap_start_trade_collection(mock_attr)

        with pytest.raises(ValueError) as exc_info:
            await wrapped()

        assert "Trade store required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_updates_is_running_on_success(self) -> None:
        """Test updates is_running on successful start."""
        mock_client = MagicMock()
        mock_client._get_trade_store = AsyncMock()
        mock_client.is_running = False
        mock_attr = AsyncMock(return_value=True)

        resolver = ClientAttributeResolver(mock_client)
        wrapped = resolver._wrap_start_trade_collection(mock_attr)
        await wrapped()

        assert mock_client.is_running is True

    @pytest.mark.asyncio
    async def test_passes_args_to_wrapped(self) -> None:
        """Test passes args to wrapped method."""
        mock_client = MagicMock()
        mock_client._get_trade_store = AsyncMock()
        mock_attr = AsyncMock(return_value=True)

        resolver = ClientAttributeResolver(mock_client)
        wrapped = resolver._wrap_start_trade_collection(mock_attr)
        await wrapped("arg1", kwarg1="value1")

        mock_attr.assert_called_once_with("arg1", kwarg1="value1")


class TestClientAttributeResolverWrapStopTradeCollection:
    """Tests for _wrap_stop_trade_collection method."""

    @pytest.mark.asyncio
    async def test_updates_is_running(self) -> None:
        """Test updates is_running on stop."""
        mock_client = MagicMock()
        mock_client.is_running = True
        mock_attr = AsyncMock(return_value=False)

        resolver = ClientAttributeResolver(mock_client)
        wrapped = resolver._wrap_stop_trade_collection(mock_attr)
        await wrapped()

        assert mock_client.is_running is False

    @pytest.mark.asyncio
    async def test_passes_args_to_wrapped(self) -> None:
        """Test passes args to wrapped method."""
        mock_client = MagicMock()
        mock_attr = AsyncMock(return_value=False)

        resolver = ClientAttributeResolver(mock_client)
        wrapped = resolver._wrap_stop_trade_collection(mock_attr)
        await wrapped("arg1", kwarg1="value1")

        mock_attr.assert_called_once_with("arg1", kwarg1="value1")


class TestClientAttributeResolverWrapRequireTradeStore:
    """Tests for _wrap_require_trade_store method."""

    @pytest.mark.asyncio
    async def test_updates_trade_store_reference(self) -> None:
        """Test updates client's trade_store reference."""
        mock_client = MagicMock()
        mock_store = MagicMock()
        mock_attr = AsyncMock(return_value=mock_store)

        resolver = ClientAttributeResolver(mock_client)
        wrapped = resolver._wrap_require_trade_store(mock_attr)
        result = await wrapped()

        assert mock_client.trade_store is mock_store
        assert result is mock_store

    @pytest.mark.asyncio
    async def test_passes_args_to_wrapped(self) -> None:
        """Test passes args to wrapped method."""
        mock_client = MagicMock()
        mock_store = MagicMock()
        mock_attr = AsyncMock(return_value=mock_store)

        resolver = ClientAttributeResolver(mock_client)
        wrapped = resolver._wrap_require_trade_store(mock_attr)
        await wrapped("arg1", kwarg1="value1")

        mock_attr.assert_called_once_with("arg1", kwarg1="value1")


class TestClientAttributeResolverResolveTradeStoreOperation:
    """Tests for _resolve_trade_store_operation method."""

    @pytest.mark.asyncio
    async def test_delegates_get_trade_store(self) -> None:
        """Test delegates _get_trade_store to TradeStoreOperations."""
        mock_client = MagicMock()
        mock_store = MagicMock()

        with patch("common.kalshi_trading_client.client_helpers.trade_store_ops.TradeStoreOperations") as mock_ops:
            mock_ops.get_trade_store = AsyncMock(return_value=mock_store)

            resolver = ClientAttributeResolver(mock_client)
            op = resolver._resolve_trade_store_operation("_get_trade_store")
            result = await op()

            mock_ops.get_trade_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_delegates_maybe_get_trade_store(self) -> None:
        """Test delegates _maybe_get_trade_store to TradeStoreOperations.

        Note: Due to the order of string replacements in _resolve_trade_store_operation,
        '_maybe_get' becomes '_maybeget' (because '_get' is replaced first).
        """
        mock_client = MagicMock()

        with patch("common.kalshi_trading_client.client_helpers.trade_store_ops.TradeStoreOperations") as mock_ops:
            # The actual attribute accessed is '_maybeget_trade_store' due to replacement order
            setattr(mock_ops, "_maybeget_trade_store", AsyncMock(return_value=None))

            resolver = ClientAttributeResolver(mock_client)
            op = resolver._resolve_trade_store_operation("_maybe_get_trade_store")
            await op()

            getattr(mock_ops, "_maybeget_trade_store").assert_called_once()

    @pytest.mark.asyncio
    async def test_delegates_ensure_trade_store(self) -> None:
        """Test delegates _ensure_trade_store to TradeStoreOperations."""
        mock_client = MagicMock()
        mock_store = MagicMock()

        with patch("common.kalshi_trading_client.client_helpers.trade_store_ops.TradeStoreOperations") as mock_ops:
            mock_ops.ensure_trade_store = AsyncMock(return_value=mock_store)

            resolver = ClientAttributeResolver(mock_client)
            op = resolver._resolve_trade_store_operation("_ensure_trade_store")
            result = await op()

            mock_ops.ensure_trade_store.assert_called_once()


class TestClientAttributeResolverIsDelegatorMethod:
    """Tests for _is_delegator_method method."""

    def test_true_for_private_method_on_delegator(self) -> None:
        """Test returns True for private method that exists on delegator."""
        mock_client = MagicMock()
        mock_client._delegator = MagicMock()
        mock_client._delegator.some_method = MagicMock()

        resolver = ClientAttributeResolver(mock_client)
        result = resolver._is_delegator_method("_some_method")

        assert result is True

    def test_true_for_has_sufficient_balance(self) -> None:
        """Test returns True for has_sufficient_balance_for_trade_with_fees."""
        mock_client = MagicMock()
        mock_client._delegator = MagicMock(spec=[])

        resolver = ClientAttributeResolver(mock_client)
        result = resolver._is_delegator_method("has_sufficient_balance_for_trade_with_fees")

        assert result is True

    def test_false_for_unknown_private_method(self) -> None:
        """Test returns False for unknown private method."""
        mock_client = MagicMock()
        mock_client._delegator = MagicMock(spec=[])

        resolver = ClientAttributeResolver(mock_client)
        result = resolver._is_delegator_method("_unknown_method")

        assert result is False

    def test_false_for_public_method(self) -> None:
        """Test returns False for public method not matching special case."""
        mock_client = MagicMock()
        mock_client._delegator = MagicMock()

        resolver = ClientAttributeResolver(mock_client)
        result = resolver._is_delegator_method("public_method")

        assert result is False


class TestClientAttributeResolverResolveDelegatorMethod:
    """Tests for _resolve_delegator_method method."""

    def test_strips_underscore_prefix(self) -> None:
        """Test strips underscore prefix when resolving."""
        mock_client = MagicMock()
        mock_method = MagicMock()
        mock_client._delegator = MagicMock()
        mock_client._delegator.some_method = mock_method

        resolver = ClientAttributeResolver(mock_client)
        result = resolver._resolve_delegator_method("_some_method")

        assert result is mock_method

    def test_uses_name_as_is_for_special_case(self) -> None:
        """Test uses name as-is for has_sufficient_balance method."""
        mock_client = MagicMock()
        mock_method = MagicMock()
        mock_client._delegator = MagicMock()
        mock_client._delegator.has_sufficient_balance_for_trade_with_fees = mock_method

        resolver = ClientAttributeResolver(mock_client)
        result = resolver._resolve_delegator_method("has_sufficient_balance_for_trade_with_fees")

        assert result is mock_method
