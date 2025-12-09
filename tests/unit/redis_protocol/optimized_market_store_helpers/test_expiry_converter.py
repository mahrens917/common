"""Tests for expiry_converter.py"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.common.exceptions import DataError
from src.common.redis_protocol.optimized_market_store_helpers.expiry_converter import (
    ExpiryConverter,
)


class TestExpiryConverterConvertIsoToDeribit:
    """Tests for convert_iso_to_deribit method"""

    def test_converts_iso_with_z_suffix(self):
        result = ExpiryConverter.convert_iso_to_deribit("2024-03-15T08:00:00Z")
        assert result == "15MAR24"

    def test_converts_iso_with_timezone_offset(self):
        result = ExpiryConverter.convert_iso_to_deribit("2024-03-15T08:00:00+00:00")
        assert result == "15MAR24"

    def test_converts_single_digit_day(self):
        result = ExpiryConverter.convert_iso_to_deribit("2024-01-05T08:00:00Z")
        assert result == "5JAN24"

    def test_converts_double_digit_day(self):
        result = ExpiryConverter.convert_iso_to_deribit("2024-12-31T08:00:00Z")
        assert result == "31DEC24"

    def test_converts_all_months(self):
        expected_months = [
            ("2024-01-15T08:00:00Z", "15JAN24"),
            ("2024-02-15T08:00:00Z", "15FEB24"),
            ("2024-03-15T08:00:00Z", "15MAR24"),
            ("2024-04-15T08:00:00Z", "15APR24"),
            ("2024-05-15T08:00:00Z", "15MAY24"),
            ("2024-06-15T08:00:00Z", "15JUN24"),
            ("2024-07-15T08:00:00Z", "15JUL24"),
            ("2024-08-15T08:00:00Z", "15AUG24"),
            ("2024-09-15T08:00:00Z", "15SEP24"),
            ("2024-10-15T08:00:00Z", "15OCT24"),
            ("2024-11-15T08:00:00Z", "15NOV24"),
            ("2024-12-15T08:00:00Z", "15DEC24"),
        ]
        for iso_date, expected in expected_months:
            result = ExpiryConverter.convert_iso_to_deribit(iso_date)
            assert result == expected

    def test_converts_different_years(self):
        result_2025 = ExpiryConverter.convert_iso_to_deribit("2025-03-15T08:00:00Z")
        assert result_2025 == "15MAR25"

        result_2099 = ExpiryConverter.convert_iso_to_deribit("2099-03-15T08:00:00Z")
        assert result_2099 == "15MAR99"

        result_2000 = ExpiryConverter.convert_iso_to_deribit("2000-03-15T08:00:00Z")
        assert result_2000 == "15MAR00"

    def test_converts_different_times(self):
        result_morning = ExpiryConverter.convert_iso_to_deribit("2024-03-15T08:00:00Z")
        assert result_morning == "15MAR24"

        result_midnight = ExpiryConverter.convert_iso_to_deribit("2024-03-15T00:00:00Z")
        assert result_midnight == "15MAR24"

        result_evening = ExpiryConverter.convert_iso_to_deribit("2024-03-15T23:59:59Z")
        assert result_evening == "15MAR24"

    def test_raises_data_error_on_invalid_iso_format(self):
        with pytest.raises(DataError) as exc_info:
            ExpiryConverter.convert_iso_to_deribit("not-a-date")
        assert "Failed to convert ISO to Deribit format" in str(exc_info.value)
        assert "not-a-date" in str(exc_info.value)

    def test_raises_data_error_on_empty_string(self):
        with pytest.raises(DataError) as exc_info:
            ExpiryConverter.convert_iso_to_deribit("")
        assert "Failed to convert ISO to Deribit format" in str(exc_info.value)

    def test_raises_data_error_on_malformed_date(self):
        with pytest.raises(DataError) as exc_info:
            ExpiryConverter.convert_iso_to_deribit("2024-13-45T08:00:00Z")
        assert "Failed to convert ISO to Deribit format" in str(exc_info.value)

    def test_raises_data_error_preserves_original_exception(self):
        with pytest.raises(DataError) as exc_info:
            ExpiryConverter.convert_iso_to_deribit("invalid")
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ValueError)


class TestExpiryConverterConvertExpiryToIso:
    """Tests for convert_expiry_to_iso method"""

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2020, 1, 1, tzinfo=timezone.utc),
    )
    def test_converts_valid_deribit_format(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=True,
        ):
            result = ExpiryConverter.convert_expiry_to_iso("15MAR24")
            assert result == "2024-03-15T08:00:00+00:00"

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_converts_single_digit_day_deribit(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=True,
        ):
            result = ExpiryConverter.convert_expiry_to_iso("5JAN25")
            assert result == "2025-01-05T08:00:00+00:00"

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_converts_all_months_deribit(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=True,
        ):
            expected_conversions = [
                ("15JAN25", "2025-01-15T08:00:00+00:00"),
                ("15FEB25", "2025-02-15T08:00:00+00:00"),
                ("15MAR25", "2025-03-15T08:00:00+00:00"),
                ("15APR25", "2025-04-15T08:00:00+00:00"),
                ("15MAY25", "2025-05-15T08:00:00+00:00"),
                ("15JUN25", "2025-06-15T08:00:00+00:00"),
                ("15JUL25", "2025-07-15T08:00:00+00:00"),
                ("15AUG25", "2025-08-15T08:00:00+00:00"),
                ("15SEP25", "2025-09-15T08:00:00+00:00"),
                ("15OCT25", "2025-10-15T08:00:00+00:00"),
                ("15NOV25", "2025-11-15T08:00:00+00:00"),
                ("15DEC25", "2025-12-15T08:00:00+00:00"),
            ]
            for deribit_date, expected_iso in expected_conversions:
                result = ExpiryConverter.convert_expiry_to_iso(deribit_date)
                assert result == expected_iso

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_converts_different_years_deribit(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=True,
        ):
            result_25 = ExpiryConverter.convert_expiry_to_iso("15MAR25")
            assert result_25 == "2025-03-15T08:00:00+00:00"

            result_99 = ExpiryConverter.convert_expiry_to_iso("15MAR99")
            assert result_99 == "2099-03-15T08:00:00+00:00"

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_returns_original_string_if_no_regex_match(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=True,
        ):
            result = ExpiryConverter.convert_expiry_to_iso("not-a-deribit-format")
            assert result == "not-a-deribit-format"

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_returns_original_string_if_already_iso_format(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=True,
        ):
            iso_string = "2024-03-15T08:00:00Z"
            result = ExpiryConverter.convert_expiry_to_iso(iso_string)
            assert result == iso_string

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_returns_original_if_before_epoch_start(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=True,
        ):
            result = ExpiryConverter.convert_expiry_to_iso("15DEC24")
            assert result == "15DEC24"

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_returns_original_if_validate_expiry_hour_fails(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=False,
        ):
            result = ExpiryConverter.convert_expiry_to_iso("15MAR25")
            assert result == "15MAR25"

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_raises_data_error_on_invalid_month(self):
        with pytest.raises(DataError) as exc_info:
            ExpiryConverter.convert_expiry_to_iso("15XXX25")
        assert "Failed to convert Deribit to ISO format" in str(exc_info.value)
        assert "15XXX25" in str(exc_info.value)

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_raises_data_error_on_invalid_day(self):
        with pytest.raises(DataError) as exc_info:
            ExpiryConverter.convert_expiry_to_iso("45JAN25")
        assert "Failed to convert Deribit to ISO format" in str(exc_info.value)

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_raises_data_error_preserves_original_exception(self):
        with pytest.raises(DataError) as exc_info:
            ExpiryConverter.convert_expiry_to_iso("32FEB25")
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ValueError)

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_handles_leap_year_correctly(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=True,
        ):
            result = ExpiryConverter.convert_expiry_to_iso("29FEB28")
            assert result == "2028-02-29T08:00:00+00:00"

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_validates_timezone_is_utc(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=True,
        ):
            result = ExpiryConverter.convert_expiry_to_iso("15MAR25")
            parsed_dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
            assert parsed_dt.tzinfo == timezone.utc

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_validates_hour_is_deribit_expiry_hour(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=True,
        ):
            result = ExpiryConverter.convert_expiry_to_iso("15MAR25")
            parsed_dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
            assert parsed_dt.hour == 8


class TestExpiryConverterRoundTrip:
    """Tests for round-trip conversions"""

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_iso_to_deribit_to_iso_roundtrip(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=True,
        ):
            original = "2025-03-15T08:00:00+00:00"
            deribit = ExpiryConverter.convert_iso_to_deribit(original)
            result = ExpiryConverter.convert_expiry_to_iso(deribit)
            assert result == original

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_deribit_to_iso_to_deribit_roundtrip(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=True,
        ):
            original = "15MAR25"
            iso = ExpiryConverter.convert_expiry_to_iso(original)
            result = ExpiryConverter.convert_iso_to_deribit(iso)
            assert result == original

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_multiple_roundtrip_conversions(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=True,
        ):
            test_dates = [
                "2025-01-15T08:00:00+00:00",
                "2025-06-30T08:00:00+00:00",
                "2025-12-31T08:00:00+00:00",
            ]
            for original in test_dates:
                deribit = ExpiryConverter.convert_iso_to_deribit(original)
                back_to_iso = ExpiryConverter.convert_expiry_to_iso(deribit)
                assert back_to_iso == original


class TestExpiryConverterEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_class_is_static_only(self):
        converter = ExpiryConverter()
        assert isinstance(converter, ExpiryConverter)

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_handles_end_of_month_dates(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=True,
        ):
            result_jan = ExpiryConverter.convert_expiry_to_iso("31JAN25")
            assert "2025-01-31" in result_jan

            result_feb = ExpiryConverter.convert_expiry_to_iso("28FEB25")
            assert "2025-02-28" in result_feb

            result_apr = ExpiryConverter.convert_expiry_to_iso("30APR25")
            assert "2025-04-30" in result_apr

    def test_iso_conversion_handles_microseconds(self):
        result = ExpiryConverter.convert_iso_to_deribit("2024-03-15T08:00:00.123456Z")
        assert result == "15MAR24"

    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(1999, 1, 1, tzinfo=timezone.utc),
    )
    def test_handles_year_2100(self):
        with patch(
            "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.validate_expiry_hour",
            return_value=True,
        ):
            result = ExpiryConverter.convert_expiry_to_iso("15MAR00")
            assert "2000-03-15" in result

    def test_iso_to_deribit_with_different_timezone_offsets(self):
        result1 = ExpiryConverter.convert_iso_to_deribit("2024-03-15T08:00:00+00:00")
        result2 = ExpiryConverter.convert_iso_to_deribit("2024-03-15T10:00:00+02:00")
        assert result1 == result2 == "15MAR24"

    @patch("src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.logger")
    def test_logs_exception_on_iso_conversion_error(self, mock_logger):
        with pytest.raises(DataError):
            ExpiryConverter.convert_iso_to_deribit("invalid")
        mock_logger.exception.assert_called_once()

    @patch("src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.logger")
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.DERIBIT_EXPIRY_HOUR",
        8,
    )
    @patch(
        "src.common.redis_protocol.optimized_market_store_helpers.expiry_converter.EPOCH_START",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    def test_logs_exception_on_deribit_conversion_error(self, mock_logger):
        with pytest.raises(DataError):
            ExpiryConverter.convert_expiry_to_iso("45JAN25")
        mock_logger.exception.assert_called_once()
