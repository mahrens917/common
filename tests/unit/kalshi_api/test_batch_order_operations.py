"""Tests for batch order operations."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.data_models.trading import (
    _MAX_BATCH_SIZE,
    BatchOrderResult,
    OrderAction,
    OrderRequest,
    OrderSide,
    OrderType,
    TimeInForce,
)
from common.kalshi_api.client_helpers.errors import KalshiClientError
from common.kalshi_api.order_operations import OrderOperations, _parse_batch_response


def _make_order_request(ticker: str = "KXTEST-T50") -> OrderRequest:
    return OrderRequest(
        ticker=ticker,
        action=OrderAction.BUY,
        side=OrderSide.YES,
        count=1,
        client_order_id=f"test-{ticker}",
        trade_rule="test_rule",
        trade_reason="test_reason",
        order_type=OrderType.LIMIT,
        yes_price_cents=50,
        time_in_force=TimeInForce.IMMEDIATE_OR_CANCEL,
    )


class TestBatchCreateOrders:
    @pytest.fixture
    def mock_request_builder(self):
        builder = MagicMock()
        builder.build_request_context = MagicMock(return_value=("POST", "http://test", {}, "batch_create_orders"))
        builder.execute_request = AsyncMock(return_value={"orders": []})
        return builder

    @pytest.fixture
    def mock_response_parser(self):
        return MagicMock()

    @pytest.fixture
    def order_ops(self, mock_request_builder, mock_response_parser):
        return OrderOperations(mock_request_builder, mock_response_parser)

    @pytest.mark.asyncio
    async def test_empty_list_raises(self, order_ops):
        with pytest.raises(KalshiClientError, match="at least one"):
            await order_ops.batch_create_orders([])

    @pytest.mark.asyncio
    async def test_exceeds_max_raises(self, order_ops):
        orders = [_make_order_request(f"TICKER-{i}") for i in range(_MAX_BATCH_SIZE + 1)]
        with pytest.raises(KalshiClientError, match="exceeds maximum"):
            await order_ops.batch_create_orders(orders)

    @pytest.mark.asyncio
    async def test_single_order_success(self, order_ops, mock_request_builder):
        mock_request_builder.execute_request = AsyncMock(
            return_value={
                "orders": [{"order_id": "ord-1", "status": "executed"}],
            }
        )
        results = await order_ops.batch_create_orders([_make_order_request()])
        assert len(results) == 1
        assert results[0].succeeded is True
        assert results[0].order_response.order_id == "ord-1"

    @pytest.mark.asyncio
    async def test_multiple_orders_success(self, order_ops, mock_request_builder):
        mock_request_builder.execute_request = AsyncMock(
            return_value={
                "orders": [
                    {"order_id": "ord-1", "status": "executed"},
                    {"order_id": "ord-2", "status": "resting"},
                ],
            }
        )
        orders = [_make_order_request("A"), _make_order_request("B")]
        results = await order_ops.batch_create_orders(orders)
        assert len(results) == 2
        assert all(r.succeeded for r in results)

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(self, order_ops, mock_request_builder):
        mock_request_builder.execute_request = AsyncMock(
            return_value={
                "orders": [
                    {"order_id": "ord-1", "status": "executed"},
                    {"error_code": "insufficient_balance", "error_message": "Not enough funds"},
                ],
            }
        )
        orders = [_make_order_request("A"), _make_order_request("B")]
        results = await order_ops.batch_create_orders(orders)
        assert results[0].succeeded is True
        assert results[1].succeeded is False
        assert results[1].error_code == "insufficient_balance"

    @pytest.mark.asyncio
    async def test_all_errors(self, order_ops, mock_request_builder):
        mock_request_builder.execute_request = AsyncMock(
            return_value={
                "orders": [
                    {"error_code": "rejected", "error_message": "Order rejected"},
                ],
            }
        )
        results = await order_ops.batch_create_orders([_make_order_request()])
        assert len(results) == 1
        assert results[0].succeeded is False


class TestParseBatchResponse:
    def test_not_dict_raises(self):
        with pytest.raises(KalshiClientError, match="not a JSON object"):
            _parse_batch_response([], [_make_order_request()])

    def test_missing_orders_key_raises(self):
        with pytest.raises(KalshiClientError, match="missing 'orders'"):
            _parse_batch_response({}, [_make_order_request()])

    def test_count_mismatch_raises(self):
        with pytest.raises(KalshiClientError, match="does not match"):
            _parse_batch_response({"orders": [{}, {}]}, [_make_order_request()])

    def test_non_dict_entry_raises(self):
        with pytest.raises(KalshiClientError, match="not a JSON object"):
            _parse_batch_response({"orders": ["bad"]}, [_make_order_request()])

    def test_preserves_order_index(self):
        orders = [_make_order_request("A"), _make_order_request("B")]
        response = {
            "orders": [
                {"order_id": "ord-1", "status": "executed"},
                {"order_id": "ord-2", "status": "executed"},
            ]
        }
        results = _parse_batch_response(response, orders)
        assert results[0].order_index == 0
        assert results[1].order_index == 1

    def test_error_entry_has_no_order_response(self):
        response = {"orders": [{"error_code": "rejected", "error_message": "nope"}]}
        results = _parse_batch_response(response, [_make_order_request()])
        assert results[0].order_response is None
        assert results[0].error_code == "rejected"
