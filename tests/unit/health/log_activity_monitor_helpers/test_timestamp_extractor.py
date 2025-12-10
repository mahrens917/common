import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from common.health.log_activity_monitor_helpers.timestamp_extractor import (
    extract_last_log_timestamp,
)


class TestTimestampExtractor(unittest.TestCase):
    @patch("os.stat")
    def test_extract_last_log_timestamp_success(self, mock_stat):
        mock_stat.return_value.st_mtime = 1609459200  # 2021-01-01 00:00:00 UTC
        result = extract_last_log_timestamp("test.log")
        expected = datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(result, expected)

    @patch("os.stat")
    def test_extract_last_log_timestamp_oserror(self, mock_stat):
        mock_stat.side_effect = OSError("File not found")
        result = extract_last_log_timestamp("test.log")
        self.assertIsNone(result)
