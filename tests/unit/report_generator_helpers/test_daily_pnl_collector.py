import unittest
from datetime import date
from unittest.mock import AsyncMock, Mock

from common.report_generator_helpers.daily_pnl_collector import DailyPnLCollector


class TestDailyPnLCollector(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_pnl_calculator = Mock()
        self.mock_trade_store = Mock()
        self.mock_pnl_calculator.trade_store = self.mock_trade_store
        self.collector = DailyPnLCollector(self.mock_pnl_calculator)

    async def test_get_daily_pnl_with_unrealized_percentage_success(self):
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 2)

        # Mock PnL unified return
        self.mock_pnl_calculator.get_unified_pnl_for_date = AsyncMock(side_effect=[1000, 2000])

        # Mock trades
        mock_trade1 = Mock()
        mock_trade1.cost_cents = 10000
        mock_trade2 = Mock()
        mock_trade2.cost_cents = 20000

        self.mock_trade_store.get_trades_by_date_range = AsyncMock(side_effect=[[mock_trade1], [mock_trade2]])

        result = await self.collector.get_daily_pnl_with_unrealized_percentage(start_date, end_date)

        self.assertEqual(len(result), 2)
        # Day 1: 1000 / 10000 = 10%
        self.assertEqual(result[0], (date(2023, 1, 1), 10.0))
        # Day 2: 2000 / 20000 = 10%
        self.assertEqual(result[1], (date(2023, 1, 2), 10.0))

    async def test_get_daily_pnl_with_unrealized_percentage_zero_cost(self):
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 1)

        self.mock_pnl_calculator.get_unified_pnl_for_date = AsyncMock(return_value=1000)
        self.mock_trade_store.get_trades_by_date_range = AsyncMock(return_value=[])

        result = await self.collector.get_daily_pnl_with_unrealized_percentage(start_date, end_date)

        self.assertEqual(result[0], (date(2023, 1, 1), 0.0))

    async def test_get_daily_pnl_with_unrealized_percentage_error(self):
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 1)

        self.mock_pnl_calculator.get_unified_pnl_for_date = AsyncMock(side_effect=ValueError("Error"))

        with self.assertRaises(ValueError):
            await self.collector.get_daily_pnl_with_unrealized_percentage(start_date, end_date)

    async def test_get_daily_pnl_with_unrealized_success(self):
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 2)

        self.mock_pnl_calculator.get_unified_pnl_for_date = AsyncMock(side_effect=[1000, 2000])

        result = await self.collector.get_daily_pnl_with_unrealized(start_date, end_date)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], (date(2023, 1, 1), 1000))
        self.assertEqual(result[1], (date(2023, 1, 2), 2000))

    async def test_get_daily_pnl_with_unrealized_error(self):
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 1)

        self.mock_pnl_calculator.get_unified_pnl_for_date = AsyncMock(side_effect=ValueError("Error"))

        with self.assertRaises(ValueError):
            await self.collector.get_daily_pnl_with_unrealized(start_date, end_date)
