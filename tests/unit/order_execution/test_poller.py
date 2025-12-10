from unittest.mock import AsyncMock

import pytest

from common.order_execution import OrderPoller
from common.trading_exceptions import KalshiOrderPollingError

_TEST_COUNT_3 = 3


@pytest.mark.asyncio
async def test_poller_returns_outcome_with_average_price():
    fetch = AsyncMock(
        return_value=[
            {"count": 2, "side": "yes", "yes_price": 40},
            {"count": 1, "side": "no", "no_price": 20},
        ]
    )
    sleep = AsyncMock()
    poller = OrderPoller(fetch, sleep=sleep, operation_name="test_poll")

    outcome = await poller.poll("ORD-1", timeout_seconds=0.5)

    sleep.assert_awaited_once_with(0.5)
    fetch.assert_awaited_once_with("ORD-1")
    assert outcome.total_filled == _TEST_COUNT_3
    assert outcome.average_price_cents == (2 * 40 + 1 * 20) // 3


@pytest.mark.asyncio
async def test_poller_returns_none_when_no_fills():
    fetch = AsyncMock(return_value=[])
    sleep = AsyncMock()
    poller = OrderPoller(fetch, sleep=sleep, operation_name="test_poll")

    outcome = await poller.poll("ORD-2", timeout_seconds=0.1)

    sleep.assert_awaited_once_with(0.1)
    fetch.assert_awaited_once_with("ORD-2")
    assert outcome is None


@pytest.mark.asyncio
async def test_poller_raises_when_fetch_fails():
    fetch = AsyncMock(side_effect=RuntimeError("network down"))
    poller = OrderPoller(fetch, sleep=AsyncMock(), operation_name="poll_failure")

    with pytest.raises(KalshiOrderPollingError) as excinfo:
        await poller.poll("ORD-3", timeout_seconds=0)

    assert "network down" in str(excinfo.value)
    assert excinfo.value.order_id == "ORD-3"


@pytest.mark.asyncio
async def test_poller_raises_for_invalid_fill():
    fetch = AsyncMock(return_value=[{"count": 0, "side": "yes", "yes_price": 45}])
    poller = OrderPoller(fetch, sleep=AsyncMock(), operation_name="poll_invalid")

    with pytest.raises(KalshiOrderPollingError) as excinfo:
        await poller.poll("ORD-4", timeout_seconds=0)

    assert "non-positive" in str(excinfo.value)
