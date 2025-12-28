"""Tests for polling_workflow module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from common.data_models.trading import OrderResponse, OrderStatus
from common.order_execution import PollingOutcome
from common.trading.polling_workflow import PollingResult, PollingWorkflow
from common.trading_exceptions import KalshiOrderPollingError


class TestPollingResult:
    """Tests for PollingResult dataclass."""

    def test_create_polling_result(self):
        order = MagicMock(spec=OrderResponse)
        outcome = MagicMock(spec=PollingOutcome)

        result = PollingResult(order=order, outcome=outcome, was_cancelled=False)

        assert result.order is order
        assert result.outcome is outcome
        assert result.was_cancelled is False

    def test_create_cancelled_result(self):
        order = MagicMock(spec=OrderResponse)

        result = PollingResult(order=order, outcome=None, was_cancelled=True)

        assert result.was_cancelled is True
        assert result.outcome is None


class TestPollingWorkflow:
    """Tests for PollingWorkflow class."""

    @pytest.fixture
    def mock_poller(self):
        poller = MagicMock()
        poller.poll = AsyncMock()
        return poller

    @pytest.fixture
    def mock_cancel_order(self):
        return AsyncMock()

    @pytest.fixture
    def mock_fetch_order(self):
        return AsyncMock()

    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def workflow(self, mock_poller, mock_cancel_order, mock_fetch_order, mock_logger):
        return PollingWorkflow(
            poller=mock_poller,
            cancel_order=mock_cancel_order,
            fetch_order=mock_fetch_order,
            logger=mock_logger,
        )

    @pytest.mark.asyncio
    async def test_execute_order_filled(self, workflow, mock_poller):
        order = MagicMock(spec=OrderResponse)
        order.order_id = "order-123"
        polling_outcome = MagicMock(spec=PollingOutcome)
        mock_poller.poll.return_value = polling_outcome

        result = await workflow.execute(
            order=order,
            timeout_seconds=5,
            operation_name="test_op",
        )

        assert result.order is order
        assert result.outcome is polling_outcome
        assert result.was_cancelled is False

    @pytest.mark.asyncio
    async def test_execute_timeout_then_cancel_success(self, workflow, mock_poller, mock_cancel_order, mock_fetch_order):
        order = MagicMock(spec=OrderResponse)
        order.order_id = "order-timeout"
        mock_poller.poll.return_value = None
        mock_cancel_order.return_value = True

        cancelled_order = MagicMock(spec=OrderResponse)
        cancelled_order.status = OrderStatus.CANCELLED
        mock_fetch_order.return_value = cancelled_order

        result = await workflow.execute(
            order=order,
            timeout_seconds=5,
            operation_name="test_op",
        )

        assert result.order is cancelled_order
        assert result.outcome is None
        assert result.was_cancelled is True
        mock_cancel_order.assert_called_once_with("order-timeout")

    @pytest.mark.asyncio
    async def test_execute_cancel_returns_false(self, workflow, mock_poller, mock_cancel_order):
        order = MagicMock(spec=OrderResponse)
        order.order_id = "order-cancel-fail"
        mock_poller.poll.return_value = None
        mock_cancel_order.return_value = False

        with pytest.raises(KalshiOrderPollingError, match="cancellation returned no success"):
            await workflow.execute(
                order=order,
                timeout_seconds=5,
                operation_name="test_op",
            )

    @pytest.mark.asyncio
    async def test_execute_cancel_but_order_not_cancelled(self, workflow, mock_poller, mock_cancel_order, mock_fetch_order):
        order = MagicMock(spec=OrderResponse)
        order.order_id = "order-still-open"
        mock_poller.poll.return_value = None
        mock_cancel_order.return_value = True

        still_open_order = MagicMock(spec=OrderResponse)
        mock_status = MagicMock()
        mock_status.value = "resting"
        still_open_order.status = mock_status
        mock_fetch_order.return_value = still_open_order

        with pytest.raises(KalshiOrderPollingError, match="unexpected status"):
            await workflow.execute(
                order=order,
                timeout_seconds=5,
                operation_name="test_op",
            )
