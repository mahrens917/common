import unittest

from src.common.report_generator_helpers.message_formatter import MessageFormatter


class TestMessageFormatter(unittest.TestCase):
    def test_format_error_message(self):
        error_msg = "Something went wrong"
        result = MessageFormatter.format_error_message(error_msg)
        self.assertIn("❌ **Error**", result)
        self.assertIn(error_msg, result)
        self.assertIn("Please try again or contact support.", result)

    def test_format_no_data_message(self):
        date_range = "2023-01-01"
        result = MessageFormatter.format_no_data_message(date_range)
        self.assertIn("📭 **No Trade Data**", result)
        self.assertIn(date_range, result)
        self.assertIn("No KXHIGH* trades found", result)
