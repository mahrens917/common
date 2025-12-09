"""Tests for position closer module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.common.data_models.trading import OrderSide, OrderStatus
from src.common.emergency_position_manager_helpers import position_closer as position_closer_module
from src.common.emergency_position_manager_helpers.position_closer import (
    PositionCloser,
)

DEFAULT_TEST_POSITION_COUNT = 10
DEFAULT_CLOSE_FILLED_COUNT = 10
ZERO_FILLED_COUNT = 0


class TestPositionCloserInit:
    """Tests for PositionCloser initialization."""

    def test_initializes_with_trading_client(self) -> None:
        """Initializes with trading client."""
        client = MagicMock()

        closer = PositionCloser(trading_client=client)

        assert closer.trading_client is client


class TestPositionCloserCountFills:
    """Tests for PositionCloser._count_fills."""

    def test_counts_single_fill(self) -> None:
        """Counts single fill."""
        client = MagicMock()
        closer = PositionCloser(trading_client=client)
        fills = [{"count": 10}]

        result = closer._count_fills(fills, "order123")

        assert result == 10

    def test_counts_multiple_fills(self) -> None:
        """Counts multiple fills."""
        client = MagicMock()
        closer = PositionCloser(trading_client=client)
        fills = [{"count": 10}, {"count": 5}, {"count": 3}]

        result = closer._count_fills(fills, "order123")

        assert result == 18

    def test_skips_fill_missing_count(self) -> None:
        """Skips fill entries missing count field."""
        client = MagicMock()
        closer = PositionCloser(trading_client=client)
        fills = [{"count": 10}, {"other": "data"}, {"count": 5}]

        with patch("src.common.emergency_position_manager_helpers.position_closer.logger"):
            result = closer._count_fills(fills, "order123")

        assert result == 15

    def test_handles_invalid_count_value(self) -> None:
        """Handles invalid count values gracefully."""
        client = MagicMock()
        closer = PositionCloser(trading_client=client)
        fills = [{"count": 10}, {"count": "invalid"}, {"count": 5}]

        with patch("src.common.emergency_position_manager_helpers.position_closer.logger"):
            result = closer._count_fills(fills, "order123")

        assert result == 15

    def test_returns_zero_for_empty_fills(self) -> None:
        """Returns zero for empty fills list."""
        client = MagicMock()
        closer = PositionCloser(trading_client=client)
        fills = []

        result = closer._count_fills(fills, "order123")

        assert result == 0


class TestPositionCloserEmergencyClosePosition:
    """Tests for PositionCloser.emergency_close_position."""

    @pytest.mark.asyncio
    async def test_creates_market_order_for_position(self) -> None:
        """Creates market order to close position."""
        client = MagicMock()
        client.create_order_with_polling = AsyncMock(
            return_value=MagicMock(filled_count=DEFAULT_CLOSE_FILLED_COUNT)
        )
        closer = PositionCloser(trading_client=client)
        position = MagicMock()
        position.ticker = "KXBTC-25JAN01"
        position.side = OrderSide.YES
        position.position_count = DEFAULT_TEST_POSITION_COUNT

        with patch("src.common.emergency_position_manager_helpers.position_closer.logger"):
            success, response, message = await closer.emergency_close_position(
                position, "Test reason"
            )

        assert success is True
        assert "successfully" in message
        client.create_order_with_polling.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_order_not_filled(self) -> None:
        """Returns false when order doesn't fill."""
        client = MagicMock()
        client.create_order_with_polling = AsyncMock(
            return_value=MagicMock(filled_count=ZERO_FILLED_COUNT)
        )
        closer = PositionCloser(trading_client=client)
        position = MagicMock()
        position.ticker = "KXBTC-25JAN01"
        position.side = OrderSide.YES
        position.position_count = DEFAULT_TEST_POSITION_COUNT

        with patch("src.common.emergency_position_manager_helpers.position_closer.logger"):
            success, response, message = await closer.emergency_close_position(
                position, "Test reason"
            )

        assert success is False
        assert "did not execute" in message

    @pytest.mark.asyncio
    async def test_handles_trading_error(self) -> None:
        """Handles trading errors gracefully."""
        from src.common.trading_exceptions import KalshiTradingError

        client = MagicMock()
        client.create_order_with_polling = AsyncMock(side_effect=KalshiTradingError("API error"))
        closer = PositionCloser(trading_client=client)
        position = MagicMock()
        position.ticker = "KXBTC-25JAN01"
        position.side = OrderSide.YES
        position.position_count = DEFAULT_TEST_POSITION_COUNT

        with patch("src.common.emergency_position_manager_helpers.position_closer.logger"):
            success, response, message = await closer.emergency_close_position(
                position, "Test reason"
            )

        assert success is False
        assert "failed" in message.lower()

    @pytest.mark.asyncio
    async def test_handles_connection_error(self) -> None:
        """Handles connection errors gracefully."""
        client = MagicMock()
        client.create_order_with_polling = AsyncMock(side_effect=ConnectionError("Network error"))
        closer = PositionCloser(trading_client=client)
        position = MagicMock()
        position.ticker = "KXBTC-25JAN01"
        position.side = OrderSide.YES
        position.position_count = DEFAULT_TEST_POSITION_COUNT

        with patch("src.common.emergency_position_manager_helpers.position_closer.logger"):
            success, response, message = await closer.emergency_close_position(
                position, "Test reason"
            )

        assert success is False


class TestPositionCloserWaitForOrderCompletion:
    """Tests for PositionCloser._wait_for_order_completion."""

    async def _dummy_sleep(self, *_args, **_kwargs):
        return None

    def _setup_asyncio(self, monkeypatch, *, step=1.0):
        class DummyLoop:
            def __init__(self, step_value: float) -> None:
                self._time = 0.0
                self._step = step_value

            def time(self) -> float:
                current = self._time
                self._time += self._step
                return current

        loop = DummyLoop(step)
        monkeypatch.setattr(
            position_closer_module.asyncio,
            "get_running_loop",
            lambda: loop,
        )
        monkeypatch.setattr(
            position_closer_module.asyncio,
            "all_tasks",
            lambda *_: set(),
        )
        monkeypatch.setattr(
            position_closer_module.asyncio,
            "sleep",
            self._dummy_sleep,
        )
        return loop

    def _prepare_client(self):
        client = MagicMock()
        client.kalshi_client = MagicMock()
        client.require_trade_store = AsyncMock(return_value=None)
        return client

    @pytest.mark.asyncio
    async def test_returns_order_when_completed(self, monkeypatch):
        client = self._prepare_client()
        client.kalshi_client.get_fills = AsyncMock(return_value=[{"count": 1}])
        order_response = MagicMock(
            status=OrderStatus.EXECUTED,
            order_id="order-123",
            trade_rule="rule",
            trade_reason="reason",
        )
        client.kalshi_client.get_order = AsyncMock(return_value=order_response)

        closer = PositionCloser(trading_client=client)
        self._setup_asyncio(monkeypatch)

        result = await closer._wait_for_order_completion("order-123", timeout_seconds=2.0)

        assert result is order_response
        client.kalshi_client.get_order.assert_called_once_with("order-123")

    @pytest.mark.asyncio
    async def test_handles_timeout_without_completion(self, monkeypatch):
        client = self._prepare_client()
        client.kalshi_client.get_fills = AsyncMock(return_value=[])
        pending_response = MagicMock(
            status=OrderStatus.PENDING,
            order_id="order-456",
            trade_rule="rule",
            trade_reason="reason",
        )
        client.kalshi_client.get_order = AsyncMock(return_value=pending_response)

        closer = PositionCloser(trading_client=client)
        self._setup_asyncio(monkeypatch, step=0.5)

        result = await closer._wait_for_order_completion("order-456", timeout_seconds=1.0)

        assert result is None

    @pytest.mark.asyncio
    async def test_retries_after_polling_error(self, monkeypatch):
        client = self._prepare_client()
        client.kalshi_client.get_fills = AsyncMock(return_value=[])

        order_response = MagicMock(
            status=OrderStatus.FILLED,
            order_id="order-789",
            trade_rule="rule",
            trade_reason="reason",
        )

        async def _flaky_get_order(*_args, **_kwargs):
            if not hasattr(_flaky_get_order, "called"):
                setattr(_flaky_get_order, "called", True)
                raise ValueError("temporary error")
            return order_response

        client.kalshi_client.get_order = AsyncMock(side_effect=_flaky_get_order)

        closer = PositionCloser(trading_client=client)
        self._setup_asyncio(monkeypatch, step=0.5)

        result = await closer._wait_for_order_completion("order-789", timeout_seconds=3.0)

        assert result is order_response
