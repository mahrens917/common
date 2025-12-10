from datetime import datetime
from unittest.mock import Mock, patch

from common.redis_protocol.parsing.kalshi_helpers.date_format_parsers import (
    parse_day_month_year_format,
    parse_intraday_format,
    parse_year_month_day_format,
)


class TestDateFormatParsers:
    def test_parse_year_month_day_format(self):
        """Test delegation to canonical YYMMMDD parser."""
        with patch(
            "common.redis_protocol.parsing.kalshi_helpers.date_format_parsers._canonical_parse_year_month_day_format"
        ) as mock_parser:
            mock_parser.return_value = datetime(2025, 1, 15)
            result = parse_year_month_day_format("25JAN15", "25", 1, "15")
            assert result == datetime(2025, 1, 15)
            mock_parser.assert_called_with("25JAN15", "25", 1, "15")

    def test_parse_intraday_format(self):
        """Test delegation to canonical DDMMMHHMM parser."""
        now = datetime(2025, 1, 15)
        with patch(
            "common.redis_protocol.parsing.kalshi_helpers.date_format_parsers._canonical_parse_intraday_format"
        ) as mock_parser:
            mock_parser.return_value = datetime(2025, 1, 15, 15, 30)
            result = parse_intraday_format("15JAN1530", now, 1, 15, "1530")
            assert result == datetime(2025, 1, 15, 15, 30)
            mock_parser.assert_called_with("15JAN1530", now, 1, 15, "1530")

    def test_parse_day_month_year_format(self):
        """Test delegation to canonical DDMMMYY parser."""
        with patch(
            "common.redis_protocol.parsing.kalshi_helpers.date_format_parsers._canonical_parse_day_month_year_format"
        ) as mock_parser:
            mock_parser.return_value = datetime(2025, 1, 15)
            result = parse_day_month_year_format("15JAN25", 1, 15, "25")
            assert result == datetime(2025, 1, 15)
            mock_parser.assert_called_with("15JAN25", 1, 15, "25")
