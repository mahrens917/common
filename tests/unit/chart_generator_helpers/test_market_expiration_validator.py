"""Tests for chart_generator_helpers.market_expiration_validator module."""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from common.chart_generator_helpers.market_expiration_validator import (
    MarketExpirationValidator,
)


class TestMarketExpirationValidatorMarketExpiresToday:
    """Tests for market_expires_today method."""

    def test_expires_today_with_expected_expiration(self) -> None:
        """Test market expires today based on expected_expiration_time."""
        validator = MarketExpirationValidator()
        et_tz = ZoneInfo("America/New_York")
        today_et = date(2025, 1, 15)
        market_data = {
            "expected_expiration_time": "2025-01-15T17:00:00Z",
        }

        result = validator.market_expires_today(
            market_data=market_data,
            today_et=today_et,
            et_timezone=et_tz,
            market_key="KXMIA-25JAN15",
            today_market_date="25JAN15",
        )

        assert result is True

    def test_does_not_expire_today(self) -> None:
        """Test market does not expire today."""
        validator = MarketExpirationValidator()
        et_tz = ZoneInfo("America/New_York")
        today_et = date(2025, 1, 15)
        market_data = {
            "expected_expiration_time": "2025-01-20T17:00:00Z",
        }

        result = validator.market_expires_today(
            market_data=market_data,
            today_et=today_et,
            et_timezone=et_tz,
            market_key="KXMIA-25JAN20",
            today_market_date="25JAN15",
        )

        assert result is False

    def test_uses_expiration_time_field(self) -> None:
        """Test uses expiration_time when expected_expiration_time missing."""
        validator = MarketExpirationValidator()
        et_tz = ZoneInfo("America/New_York")
        today_et = date(2025, 1, 15)
        market_data = {
            "expiration_time": "2025-01-15T17:00:00Z",
        }

        result = validator.market_expires_today(
            market_data=market_data,
            today_et=today_et,
            et_timezone=et_tz,
            market_key="KXMIA-25JAN15",
            today_market_date="25JAN15",
        )

        assert result is True

    def test_uses_close_time_field(self) -> None:
        """Test uses close_time when other fields missing."""
        validator = MarketExpirationValidator()
        et_tz = ZoneInfo("America/New_York")
        today_et = date(2025, 1, 15)
        market_data = {
            "close_time": "2025-01-15T17:00:00Z",
        }

        result = validator.market_expires_today(
            market_data=market_data,
            today_et=today_et,
            et_timezone=et_tz,
            market_key="KXMIA-25JAN15",
            today_market_date="25JAN15",
        )

        assert result is True

    def test_raises_on_no_metadata(self) -> None:
        """Test raises error when no expiration metadata available."""
        validator = MarketExpirationValidator()
        et_tz = ZoneInfo("America/New_York")
        today_et = date(2025, 1, 15)
        market_data: dict[str, str] = {}

        with pytest.raises(RuntimeError) as exc_info:
            validator.market_expires_today(
                market_data=market_data,
                today_et=today_et,
                et_timezone=et_tz,
                market_key="KXMIA-25JAN15",
                today_market_date="25JAN15",
            )

        assert "No expiration metadata" in str(exc_info.value)

    def test_raises_on_invalid_timestamp(self) -> None:
        """Test raises error on invalid timestamp format."""
        validator = MarketExpirationValidator()
        et_tz = ZoneInfo("America/New_York")
        today_et = date(2025, 1, 15)
        market_data = {
            "expected_expiration_time": "not-a-valid-date",
        }

        with pytest.raises(RuntimeError) as exc_info:
            validator.market_expires_today(
                market_data=market_data,
                today_et=today_et,
                et_timezone=et_tz,
                market_key="KXMIA-25JAN15",
                today_market_date="25JAN15",
            )

        assert "Invalid timestamp" in str(exc_info.value)

    def test_handles_empty_string_fields(self) -> None:
        """Test skips empty string fields."""
        validator = MarketExpirationValidator()
        et_tz = ZoneInfo("America/New_York")
        today_et = date(2025, 1, 15)
        market_data = {
            "expected_expiration_time": "",
            "expiration_time": "2025-01-15T17:00:00Z",
        }

        result = validator.market_expires_today(
            market_data=market_data,
            today_et=today_et,
            et_timezone=et_tz,
            market_key="KXMIA-25JAN15",
            today_market_date="25JAN15",
        )

        assert result is True

    def test_handles_none_fields(self) -> None:
        """Test skips None fields."""
        validator = MarketExpirationValidator()
        et_tz = ZoneInfo("America/New_York")
        today_et = date(2025, 1, 15)
        market_data = {
            "expected_expiration_time": None,
            "close_time": "2025-01-15T17:00:00Z",
        }

        result = validator.market_expires_today(
            market_data=market_data,
            today_et=today_et,
            et_timezone=et_tz,
            market_key="KXMIA-25JAN15",
            today_market_date="25JAN15",
        )

        assert result is True

    def test_timezone_conversion(self) -> None:
        """Test properly converts UTC to ET timezone."""
        validator = MarketExpirationValidator()
        et_tz = ZoneInfo("America/New_York")
        # Use a date where UTC and ET differ
        today_et = date(2025, 1, 15)
        # 2AM UTC on Jan 16 is 9PM ET on Jan 15
        market_data = {
            "expected_expiration_time": "2025-01-16T02:00:00Z",
        }

        result = validator.market_expires_today(
            market_data=market_data,
            today_et=today_et,
            et_timezone=et_tz,
            market_key="KXMIA-25JAN15",
            today_market_date="25JAN15",
        )

        assert result is True
