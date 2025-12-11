import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from common.data_models.trading import OrderRequest, OrderResponse, OrderStatus
from common.kalshi_trading_client.services.order_helpers.order_poller_helpers import (
    apply_polling_outcome,
    execute_polling_workflow,
    finalize_polling_result,
    is_order_complete,
)
from common.order_execution import PollingOutcome
from common.trading_exceptions import (
    KalshiOrderPollingError,
    KalshiTradeNotificationError,
    KalshiTradePersistenceError,
)

DEFAULT_TEST_ORDER_COUNT = 10
DEFAULT_AVERAGE_PRICE = 50
ZERO_FILLED_COUNT = 0


class TestOrderPollerHelpers(unittest.IsolatedAsyncioTestCase):
    def test_is_order_complete_filled(self):
        response = Mock(spec=OrderResponse)
        response.filled_count = DEFAULT_TEST_ORDER_COUNT
        response.order_id = "order_id"
        assert is_order_complete("op", response) is True

    def test_is_order_complete_cancelled(self):
        response = Mock(spec=OrderResponse)
        response.filled_count = ZERO_FILLED_COUNT
        response.status = OrderStatus.CANCELLED
        response.order_id = "order_id"
        assert is_order_complete("op", response) is True

    def test_is_order_complete_not_complete(self):
        response = Mock(spec=OrderResponse)
        response.filled_count = ZERO_FILLED_COUNT
        response.status = OrderStatus.PENDING
        assert is_order_complete("op", response) is False

    def test_apply_polling_outcome(self):
        response = Mock(spec=OrderResponse)
        response.filled_count = ZERO_FILLED_COUNT
        response.remaining_count = DEFAULT_TEST_ORDER_COUNT

        outcome = PollingOutcome(
            total_filled=DEFAULT_TEST_ORDER_COUNT,
            average_price_cents=DEFAULT_AVERAGE_PRICE,
            fills=[],
        )

        apply_polling_outcome(response, outcome)

        assert response.filled_count == DEFAULT_TEST_ORDER_COUNT
        assert response.remaining_count == 0
        assert response.average_fill_price_cents == DEFAULT_AVERAGE_PRICE
        assert response.status == OrderStatus.FILLED

    @patch("common.kalshi_trading_client.services.order_helpers.order_poller_helpers.PollingWorkflow")
    async def test_execute_polling_workflow_success(self, MockWorkflow):
        mock_workflow_instance = MockWorkflow.return_value
        mock_workflow_instance.execute = AsyncMock(return_value="result")

        client = Mock()
        poller_factory = Mock()
        response = Mock(spec=OrderResponse)
        response.order_id = "order_id"
        response.trade_rule = "rule"
        response.trade_reason = "reason"

        result = await execute_polling_workflow(client, poller_factory, "op", response, DEFAULT_TEST_ORDER_COUNT, "cancel_func")
        assert result == "result"
        MockWorkflow.assert_called()

    @patch("common.kalshi_trading_client.services.order_helpers.order_poller_helpers.PollingWorkflow")
    async def test_execute_polling_workflow_failure(self, MockWorkflow):
        mock_workflow_instance = MockWorkflow.return_value
        mock_workflow_instance.execute = AsyncMock(side_effect=KalshiOrderPollingError("error"))

        response = Mock(spec=OrderResponse)
        response.order_id = "order_id"

        with self.assertRaises(KalshiOrderPollingError):
            await execute_polling_workflow(Mock(), Mock(), "op", response, DEFAULT_TEST_ORDER_COUNT, "cancel_func")

    @patch("common.kalshi_trading_client.services.order_helpers.order_poller_helpers.PollingWorkflow")
    async def test_execute_polling_workflow_passes_fetch_order(self, MockWorkflow):
        mock_workflow_instance = MockWorkflow.return_value
        mock_workflow_instance.execute = AsyncMock(return_value="result")

        poller_factory = MagicMock()
        poller_factory.return_value = "poller"
        client = MagicMock()
        client.get_order = AsyncMock(return_value="order")

        response = Mock(spec=OrderResponse)
        response.order_id = "order_id"
        response.trade_rule = "rule"
        response.trade_reason = "reason"

        await execute_polling_workflow(client, poller_factory, "op", response, DEFAULT_TEST_ORDER_COUNT, "cancel_func")

        _, kwargs = MockWorkflow.call_args
        fetch_order = kwargs["fetch_order"]

        assert asyncio.iscoroutinefunction(fetch_order)
        await fetch_order("order_id")
        client.get_order.assert_called_with("order_id", trade_rule="rule", trade_reason="reason")

    async def test_finalize_polling_result_success(self):
        finalizer_factory = Mock()
        mock_finalizer = Mock()
        finalizer_factory.return_value = mock_finalizer
        mock_finalizer.finalize = AsyncMock()

        order_request = Mock(spec=OrderRequest)

        # polling_result has .order and .outcome
        polling_result = Mock()
        order_response = Mock(spec=OrderResponse)
        order_response.filled_count = ZERO_FILLED_COUNT
        order_response.remaining_count = DEFAULT_TEST_ORDER_COUNT
        order_response.order_id = "order_id"

        outcome = PollingOutcome(
            total_filled=DEFAULT_TEST_ORDER_COUNT,
            average_price_cents=DEFAULT_AVERAGE_PRICE,
            fills=[],
        )

        polling_result.order = order_response
        polling_result.outcome = outcome

        result = await finalize_polling_result(finalizer_factory, "op", order_request, polling_result)

        assert result == order_response
        assert order_response.filled_count == DEFAULT_TEST_ORDER_COUNT
        mock_finalizer.finalize.assert_called_with(order_request, order_response, outcome)

    async def test_finalize_polling_result_persistence_error(self):
        finalizer_factory = Mock()
        mock_finalizer = Mock()
        finalizer_factory.return_value = mock_finalizer
        mock_finalizer.finalize = AsyncMock(side_effect=KalshiTradePersistenceError("error"))

        polling_result = Mock()
        order_response = Mock(spec=OrderResponse)
        order_response.filled_count = ZERO_FILLED_COUNT
        order_response.remaining_count = DEFAULT_TEST_ORDER_COUNT
        order_response.order_id = "order_id"
        outcome = PollingOutcome(
            total_filled=DEFAULT_TEST_ORDER_COUNT,
            average_price_cents=DEFAULT_AVERAGE_PRICE,
            fills=[],
        )

        polling_result.order = order_response
        polling_result.outcome = outcome

        with self.assertRaises(KalshiTradePersistenceError):
            await finalize_polling_result(finalizer_factory, "op", Mock(), polling_result)

    async def test_finalize_polling_result_notification_error(self):
        finalizer_factory = Mock()
        mock_finalizer = Mock()
        finalizer_factory.return_value = mock_finalizer
        mock_finalizer.finalize = AsyncMock(side_effect=KalshiTradeNotificationError("error"))

        polling_result = Mock()
        order_response = Mock(spec=OrderResponse)
        order_response.filled_count = ZERO_FILLED_COUNT
        order_response.remaining_count = DEFAULT_TEST_ORDER_COUNT
        order_response.order_id = "order_id"
        outcome = PollingOutcome(
            total_filled=DEFAULT_TEST_ORDER_COUNT,
            average_price_cents=DEFAULT_AVERAGE_PRICE,
            fills=[],
        )

        polling_result.order = order_response
        polling_result.outcome = outcome

        with self.assertRaises(KalshiTradeNotificationError):
            await finalize_polling_result(finalizer_factory, "op", Mock(), polling_result)
