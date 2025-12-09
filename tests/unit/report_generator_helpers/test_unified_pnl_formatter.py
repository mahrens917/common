import unittest
from unittest.mock import Mock

from src.common.report_generator_helpers.unified_pnl_formatter import UnifiedPnLFormatter

DEFAULT_UNIFIED_PNL_TRADE_COUNT = 10


class TestUnifiedPnLFormatter(unittest.TestCase):
    def setUp(self):
        self.mock_emoji_selector = Mock()
        self.mock_dollar_converter = Mock()
        self.mock_stats_calculator = Mock()
        self.formatter = UnifiedPnLFormatter(
            self.mock_emoji_selector,
            self.mock_dollar_converter,
            self.mock_stats_calculator,
        )

    def test_format_unified_pnl_section(self):
        total_pnl_cents = 5000
        trade_count = DEFAULT_UNIFIED_PNL_TRADE_COUNT
        trades = ["trade1", "trade2"]

        self.mock_dollar_converter.calculate_total_contracts.return_value = 20
        self.mock_dollar_converter.calculate_total_cost_dollars.return_value = 100.0
        self.mock_stats_calculator.calculate_win_rate.return_value = 0.6
        self.mock_emoji_selector.get_fire_or_cold_emoji.return_value = "🔥"

        result = self.formatter.format_unified_pnl_section(
            "Test Period", total_pnl_cents, trade_count, trades
        )

        self.assertIn("🔥 **Test Period**", result)
        self.assertIn("├── P&L: $+50.00 (2 trades)", result)
        self.assertIn("├── Contracts Traded: 20", result)
        self.assertIn("├── Money Traded: $100.00", result)
        self.assertIn("├── Total P&L (%): $+50.00 (+50.0%)", result)
        self.assertIn("└── Win Rate: 60% (2 trades)", result)

    def test_format_unified_pnl_section_zero_cost(self):
        total_pnl_cents = 5000
        trade_count = DEFAULT_UNIFIED_PNL_TRADE_COUNT
        trades = ["trade1"]

        self.mock_dollar_converter.calculate_total_contracts.return_value = 20
        self.mock_dollar_converter.calculate_total_cost_dollars.return_value = 0.0
        self.mock_stats_calculator.calculate_win_rate.return_value = 0.6
        self.mock_emoji_selector.get_fire_or_cold_emoji.return_value = "🔥"

        result = self.formatter.format_unified_pnl_section(
            "Test Period", total_pnl_cents, trade_count, trades
        )

        self.assertIn("├── Total P&L (%): $+50.00", result)
        self.assertNotIn("(+", result)  # No percentage
