import unittest
from unittest.mock import Mock

from common.data_models.trade_record import PnLBreakdown
from common.report_generator_helpers.station_breakdown_formatter import (
    StationBreakdownFormatter,
)

DEFAULT_STATION_BREAKDOWN_TRADES_COUNT = 10


class TestStationBreakdownFormatter(unittest.TestCase):
    def setUp(self):
        self.mock_emoji_selector = Mock()
        self.formatter = StationBreakdownFormatter(self.mock_emoji_selector)

    def test_format_station_breakdown_empty(self):
        self.assertEqual(self.formatter.format_station_breakdown({}), [])

    def test_format_station_breakdown_populated(self):
        breakdown = Mock(spec=PnLBreakdown)
        breakdown.pnl_cents = 5000
        breakdown.cost_cents = 10000
        breakdown.trades_count = DEFAULT_STATION_BREAKDOWN_TRADES_COUNT
        breakdown.win_rate = 0.6

        by_station = {"KJFK": breakdown}
        self.mock_emoji_selector.get_pnl_emoji.return_value = "🟢"

        result = self.formatter.format_station_breakdown(by_station)

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "")
        self.assertEqual(result[1], "🏛️ **By Weather Station:**")
        self.assertIn("KJFK", result[2])
        self.assertIn("$+50.00", result[2])
        self.assertIn(f"{DEFAULT_STATION_BREAKDOWN_TRADES_COUNT} trades", result[2])
        self.mock_emoji_selector.get_pnl_emoji.assert_called_with(50.0)
