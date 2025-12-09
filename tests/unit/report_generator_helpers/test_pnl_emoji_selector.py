import unittest

from src.common.report_generator_helpers.pnl_emoji_selector import PnLEmojiSelector


class TestPnLEmojiSelector(unittest.TestCase):
    def test_get_pnl_emoji(self):
        self.assertEqual(PnLEmojiSelector.get_pnl_emoji(100), "📈")
        self.assertEqual(PnLEmojiSelector.get_pnl_emoji(0), "📈")
        self.assertEqual(PnLEmojiSelector.get_pnl_emoji(-50), "📉")

    def test_get_fire_or_cold_emoji(self):
        self.assertEqual(PnLEmojiSelector.get_fire_or_cold_emoji(100), "🔥")
        self.assertEqual(PnLEmojiSelector.get_fire_or_cold_emoji(0), "🔥")
        self.assertEqual(PnLEmojiSelector.get_fire_or_cold_emoji(-50), "❄️")
