"""Tests for kalshi_api order_operations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.data_models.trading import OrderStatus
from common.kalshi_api.client_helpers.errors import KalshiClientError
from common.kalshi_api.order_operations import OrderMetadataManager, OrderOperations


class TestOrderMetadataManager:
    @pytest.fixture
    def manager(self):
        return OrderMetadataManager(trade_store_errors=(ValueError, RuntimeError))

    def test_attach_trade_store_success(self, manager):
        store = MagicMock()
        manager.attach_trade_store(store)
        assert manager._trade_store is store

    def test_attach_trade_store_none(self, manager):
        with pytest.raises(KalshiClientError) as exc_info:
            manager.attach_trade_store(None)
        assert "must not be None" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_metadata_success(self, manager):
        store = MagicMock()
        store.get_order_metadata = AsyncMock(return_value={"trade_rule": "rule1", "trade_reason": "reason1"})
        manager._trade_store = store

        metadata = await manager.fetch_metadata("order-123")

        assert metadata == {"trade_rule": "rule1", "trade_reason": "reason1"}

    @pytest.mark.asyncio
    async def test_fetch_metadata_store_error(self, manager):
        store = MagicMock()
        store.get_order_metadata = AsyncMock(side_effect=ValueError("store error"))
        manager._trade_store = store

        with pytest.raises(KalshiClientError) as exc_info:
            await manager.fetch_metadata("order-123")

        assert "Failed to fetch" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_metadata_empty(self, manager):
        store = MagicMock()
        store.get_order_metadata = AsyncMock(return_value={})
        manager._trade_store = store

        with pytest.raises(KalshiClientError) as exc_info:
            await manager.fetch_metadata("order-123")

        assert "missing" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_require_trade_store_not_configured(self, manager):
        with pytest.raises(KalshiClientError) as exc_info:
            await manager._require_trade_store()

        assert "not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_require_trade_store_with_init(self, manager):
        store = MagicMock()
        store.initialize = MagicMock(return_value=None)
        manager._trade_store = store

        result = await manager._require_trade_store()

        assert result is store
        store.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_require_trade_store_async_init(self, manager):
        store = MagicMock()
        store.initialize = AsyncMock()
        manager._trade_store = store

        result = await manager._require_trade_store()

        assert result is store
        store.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_require_trade_store_init_error(self, manager):
        store = MagicMock()
        store.initialize = MagicMock(side_effect=ValueError("init error"))
        manager._trade_store = store

        with pytest.raises(KalshiClientError) as exc_info:
            await manager._require_trade_store()

        assert "Failed to initialize" in str(exc_info.value)


class TestOrderOperations:
    @pytest.fixture
    def mock_request_builder(self):
        builder = MagicMock()
        builder.build_request_context = MagicMock(return_value=("GET", "http://url", {}, "op"))
        builder.execute_request = AsyncMock(return_value={})
        return builder

    @pytest.fixture
    def order_ops(self, mock_request_builder):
        return OrderOperations(mock_request_builder)

    def test_init(self, order_ops):
        assert order_ops._request_builder is not None

    def test_attach_trade_store(self, order_ops):
        store = MagicMock()
        order_ops.attach_trade_store(store)
        assert order_ops._metadata_manager._trade_store is store

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, order_ops, mock_request_builder):
        mock_request_builder.execute_request = AsyncMock(return_value={"status": "cancelled"})

        result = await order_ops.cancel_order("order-123")

        assert result == {"status": "cancelled"}
        mock_request_builder.build_request_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_order_empty_id(self, order_ops):
        with pytest.raises(KalshiClientError) as exc_info:
            await order_ops.cancel_order("")

        assert "must be provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_order_empty_id(self, order_ops):
        with pytest.raises(KalshiClientError) as exc_info:
            await order_ops.get_order("")

        assert "must be provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_fills_success(self, order_ops, mock_request_builder):
        mock_request_builder.execute_request = AsyncMock(return_value={"fills": [{"fill_id": "1"}]})

        with patch("common.kalshi_api.order_operations.normalise_rp_fill", return_value={"normalized": True}) as mock_norm:
            result = await order_ops.get_fills("order-123")

            assert result == [{"normalized": True}]
            mock_norm.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_fills_empty_id(self, order_ops):
        with pytest.raises(KalshiClientError) as exc_info:
            await order_ops.get_fills("")

        assert "must be provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_fills_not_dict_response(self, order_ops, mock_request_builder):
        mock_request_builder.execute_request = AsyncMock(return_value=[])

        with pytest.raises(KalshiClientError) as exc_info:
            await order_ops.get_fills("order-123")

        assert "not a JSON object" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_fills_not_list(self, order_ops, mock_request_builder):
        mock_request_builder.execute_request = AsyncMock(return_value={"fills": "not a list"})

        with pytest.raises(KalshiClientError) as exc_info:
            await order_ops.get_fills("order-123")

        assert "not a list" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_fills_item_not_dict(self, order_ops, mock_request_builder):
        mock_request_builder.execute_request = AsyncMock(return_value={"fills": ["not a dict"]})

        with pytest.raises(KalshiClientError) as exc_info:
            await order_ops.get_fills("order-123")

        assert "must be a JSON object" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_order_success(self, order_ops, mock_request_builder):
        order_request = MagicMock()
        order_request.trade_rule = "peak"
        order_request.trade_reason = "Algorithm signal: peak"

        mock_request_builder.execute_request = AsyncMock(
            return_value={
                "order": {
                    "order_id": "new-order-123",
                    "client_order_id": "client-123",
                    "status": "executed",
                    "ticker": "ABC",
                    "side": "yes",
                    "action": "buy",
                    "type": "limit",
                    "fill_count_fp": "1.00",
                    "initial_count_fp": "1.00",
                    "taker_fill_cost_dollars": "0.9200",
                    "taker_fees_dollars": "0.0100",
                    "maker_fees_dollars": "0.0000",
                    "created_time": "2026-03-13T05:15:36.092548Z",
                },
            },
        )

        with patch("common.kalshi_api.order_operations.build_order_payload") as mock_build:
            mock_build.return_value = {"ticker": "ABC"}

            result = await order_ops.create_order(order_request)

            mock_build.assert_called_once_with(order_request)
            assert result.order_id == "new-order-123"
            assert result.filled_count == 1
            assert result.fees_cents == 1

    @pytest.mark.asyncio
    async def test_create_order_canceled(self, order_ops, mock_request_builder):
        order_request = MagicMock()
        order_request.trade_rule = "peak"
        order_request.trade_reason = "Algorithm signal: peak"

        mock_request_builder.execute_request = AsyncMock(
            return_value={
                "order": {
                    "order_id": "canceled-order-456",
                    "client_order_id": "client-456",
                    "status": "canceled",
                    "ticker": "ABC",
                    "side": "yes",
                    "action": "sell",
                    "type": "limit",
                    "fill_count_fp": "0.00",
                    "initial_count_fp": "1.00",
                    "taker_fill_cost_dollars": "0.0000",
                    "taker_fees_dollars": "0.0000",
                    "maker_fees_dollars": "0.0000",
                    "created_time": "2026-03-13T05:15:41.913259Z",
                },
            },
        )

        with patch("common.kalshi_api.order_operations.build_order_payload") as mock_build:
            mock_build.return_value = {"ticker": "ABC"}

            result = await order_ops.create_order(order_request)

            assert result.order_id == "canceled-order-456"
            assert result.status == OrderStatus.CANCELLED
            assert result.filled_count == 0
            assert result.average_fill_price_cents is None

    @pytest.mark.asyncio
    async def test_create_order_invalid_request(self, order_ops):
        order_request = MagicMock()

        with patch("common.kalshi_api.order_operations.build_order_payload") as mock_build:
            mock_build.side_effect = ValueError("invalid order")

            with pytest.raises(KalshiClientError):
                await order_ops.create_order(order_request)

    @pytest.mark.asyncio
    async def test_create_order_missing_order_id(self, order_ops, mock_request_builder):
        order_request = MagicMock()

        mock_request_builder.execute_request = AsyncMock(return_value={})

        with patch("common.kalshi_api.order_operations.build_order_payload") as mock_build:
            mock_build.return_value = {"ticker": "ABC"}

            with pytest.raises(KalshiClientError) as exc_info:
                await order_ops.create_order(order_request)

            assert "missing order_id" in str(exc_info.value)
