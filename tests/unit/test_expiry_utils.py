"""Unit tests for common expiry_utils module."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from common.exceptions import InvalidMarketDataError, ValidationError
from common.expiry_utils import (
    _compute_time_to_expiry_years,
    _ensure_timezone_awareness,
    _extract_market_expiry_value,
    _extract_strikes_from_market,
    _extract_unique_strikes_from_markets,
    _get_field_value,
    _resolve_market_ticker,
    calculate_time_to_expiry_from_market_data,
    group_markets_by_expiry,
    validate_expiry_group_strikes,
)


class TestResolveMarketTicker:
    """Tests for _resolve_market_ticker function."""

    def test_ticker_from_object_attribute(self):
        """Test extracting ticker from object with ticker attribute."""
        market = Mock(ticker="KMARKT-25JAN01")
        assert _resolve_market_ticker(market) == "KMARKT-25JAN01"

    def test_ticker_from_dict(self):
        """Test extracting ticker from dictionary."""
        market = {"ticker": "KMARKT-25JAN01"}
        assert _resolve_market_ticker(market) == "KMARKT-25JAN01"

    def test_no_ticker_returns_unknown(self):
        """Test that missing ticker returns 'unknown'."""
        market = Mock(spec=[])
        assert _resolve_market_ticker(market) == "unknown"

    def test_empty_dict_returns_unknown(self):
        """Test that empty dict returns 'unknown'."""
        market = {}
        assert _resolve_market_ticker(market) == "unknown"

    def test_none_ticker_returns_unknown(self):
        """Test that None ticker returns 'unknown'."""
        market = {"ticker": None}
        assert _resolve_market_ticker(market) == "unknown"


class TestExtractMarketExpiryValue:
    """Tests for _extract_market_expiry_value function."""

    def test_extract_from_expiry_time_attribute(self):
        """Test extracting expiry from expiry_time attribute."""
        expiry = datetime(2025, 1, 25, 12, 0, tzinfo=timezone.utc)
        market = Mock(expiry_time=expiry)
        result = _extract_market_expiry_value(market)
        assert result == expiry

    def test_extract_from_dict_close_time(self):
        """Test extracting from close_time in dict."""
        expiry = datetime(2025, 1, 25, 12, 0, tzinfo=timezone.utc)
        market = {"close_time": expiry}
        result = _extract_market_expiry_value(market)
        assert result == expiry

    def test_extract_from_dict_expiry(self):
        """Test extracting from expiry field in dict."""
        expiry = datetime(2025, 1, 25, 12, 0, tzinfo=timezone.utc)
        market = {"expiry": expiry}
        result = _extract_market_expiry_value(market)
        assert result == expiry

    def test_extract_from_dict_expiration_time(self):
        """Test extracting from expiration_time field in dict."""
        expiry = datetime(2025, 1, 25, 12, 0, tzinfo=timezone.utc)
        market = {"expiration_time": expiry}
        result = _extract_market_expiry_value(market)
        assert result == expiry

    def test_parse_string_expiry(self):
        """Test parsing string expiry value."""
        market = {"close_time": "2025-01-25T12:00:00Z"}
        result = _extract_market_expiry_value(market)
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 25

    def test_no_expiry_field_raises_error(self):
        """Test that missing expiry field raises InvalidMarketDataError."""
        market = {"ticker": "KMARKT-25JAN01"}
        with pytest.raises(InvalidMarketDataError, match="No expiry field found"):
            _extract_market_expiry_value(market)

    def test_none_expiry_raises_error(self):
        """Test that None expiry value raises error."""
        market = {"close_time": None}
        with pytest.raises(InvalidMarketDataError, match="No expiry field found"):
            _extract_market_expiry_value(market)

    def test_invalid_type_raises_error(self):
        """Test that invalid expiry type raises TypeError."""
        market = {"close_time": 12345}
        with pytest.raises(TypeError, match="Expiry value must resolve to a datetime"):
            _extract_market_expiry_value(market)


class TestEnsureTimezoneAwareness:
    """Tests for _ensure_timezone_awareness function."""

    def test_naive_datetime_gets_utc(self):
        """Test that naive datetime is converted to UTC."""
        naive_dt = datetime(2025, 1, 25, 12, 0)
        result = _ensure_timezone_awareness(naive_dt)
        assert result.tzinfo == timezone.utc
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 25
        assert result.hour == 12

    def test_aware_datetime_unchanged(self):
        """Test that timezone-aware datetime is unchanged."""
        aware_dt = datetime(2025, 1, 25, 12, 0, tzinfo=timezone.utc)
        result = _ensure_timezone_awareness(aware_dt)
        assert result == aware_dt
        assert result.tzinfo == timezone.utc


class TestComputeTimeToExpiryYears:
    """Tests for _compute_time_to_expiry_years function."""

    def test_delegates_to_canonical_implementation(self):
        """Test that function delegates to canonical implementation."""
        expiry = datetime(2025, 6, 1, tzinfo=timezone.utc)
        current = datetime(2025, 1, 1, tzinfo=timezone.utc)

        with patch("common.time_helpers.expiry_conversions.calculate_time_to_expiry_years") as mock_canonical:
            mock_canonical.return_value = 0.416
            result = _compute_time_to_expiry_years(expiry, current)

            # Note: parameter order is reversed when calling canonical
            mock_canonical.assert_called_once_with(current, expiry)
            assert result == 0.416


class TestCalculateTimeToExpiryFromMarketData:
    """Tests for calculate_time_to_expiry_from_market_data function."""

    def test_valid_calculation(self):
        """Test valid time to expiry calculation."""
        expiry = datetime(2025, 6, 1, tzinfo=timezone.utc)
        current = datetime(2025, 1, 1, tzinfo=timezone.utc)
        market = {"close_time": expiry}

        with patch(
            "common.expiry_utils._compute_time_to_expiry_years",
            return_value=0.416,
        ):
            result = calculate_time_to_expiry_from_market_data(market, current)
            assert result == 0.416

    def test_negative_time_returns_zero(self):
        """Test that negative time to expiry returns 0."""
        expiry = datetime(2024, 1, 1, tzinfo=timezone.utc)
        current = datetime(2025, 1, 1, tzinfo=timezone.utc)
        market = {"close_time": expiry}

        with patch(
            "common.expiry_utils._compute_time_to_expiry_years",
            return_value=-1.0,
        ):
            result = calculate_time_to_expiry_from_market_data(market, current)
            assert result == 0.0

    def test_handles_naive_datetimes(self):
        """Test that naive datetimes are handled correctly."""
        expiry_naive = datetime(2025, 6, 1)
        current_naive = datetime(2025, 1, 1)
        market = {"close_time": expiry_naive}

        with patch(
            "common.expiry_utils._compute_time_to_expiry_years",
            return_value=0.416,
        ):
            result = calculate_time_to_expiry_from_market_data(market, current_naive)
            assert result == 0.416

    def test_value_error_raises_invalid_market_data_error(self):
        """Test that ValueError is wrapped in InvalidMarketDataError."""
        market = {"close_time": "invalid date"}
        current = datetime(2025, 1, 1, tzinfo=timezone.utc)

        with pytest.raises(InvalidMarketDataError, match="Time to expiry calculation failed"):
            calculate_time_to_expiry_from_market_data(market, current)


class TestGroupMarketsByExpiry:
    """Tests for group_markets_by_expiry function."""

    def test_empty_market_list_raises_error(self):
        """Test that empty market list raises InvalidMarketDataError."""
        current = datetime(2025, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(InvalidMarketDataError, match="Cannot group empty market list"):
            group_markets_by_expiry([], current)

    def test_single_expiry_group(self):
        """Test grouping markets with same expiry."""
        expiry = datetime(2025, 6, 1, tzinfo=timezone.utc)
        current = datetime(2025, 1, 1, tzinfo=timezone.utc)

        markets = [
            {"ticker": "M1", "close_time": expiry, "strike": 100},
            {"ticker": "M2", "close_time": expiry, "strike": 110},
        ]

        with patch(
            "common.expiry_utils.calculate_time_to_expiry_from_market_data",
            return_value=0.416,
        ):
            result = group_markets_by_expiry(markets, current)

            assert len(result) == 1
            assert 0.416 in result
            assert len(result[0.416]) == 2

    def test_multiple_expiry_groups(self):
        """Test grouping markets with different expiries."""
        expiry1 = datetime(2025, 6, 1, tzinfo=timezone.utc)
        expiry2 = datetime(2025, 12, 1, tzinfo=timezone.utc)
        current = datetime(2025, 1, 1, tzinfo=timezone.utc)

        markets = [
            {"ticker": "M1", "close_time": expiry1, "strike": 100},
            {"ticker": "M2", "close_time": expiry2, "strike": 110},
        ]

        def mock_time_to_expiry(market, current_time):
            if market["ticker"] == "M1":
                return 0.416
            return 0.916

        with patch(
            "common.expiry_utils.calculate_time_to_expiry_from_market_data",
            side_effect=mock_time_to_expiry,
        ):
            result = group_markets_by_expiry(markets, current)

            assert len(result) == 2
            assert 0.416 in result
            assert 0.916 in result
            assert len(result[0.416]) == 1
            assert len(result[0.916]) == 1

    def test_expired_markets_skipped(self):
        """Test that expired markets are skipped."""
        expiry1 = datetime(2025, 6, 1, tzinfo=timezone.utc)
        expiry2 = datetime(2024, 1, 1, tzinfo=timezone.utc)  # Expired
        current = datetime(2025, 1, 1, tzinfo=timezone.utc)

        markets = [
            {"ticker": "M1", "close_time": expiry1, "strike": 100},
            {"ticker": "M2", "close_time": expiry2, "strike": 110},
        ]

        def mock_time_to_expiry(market, current_time):
            if market["ticker"] == "M1":
                return 0.416
            return 0.0  # Expired

        with patch(
            "common.expiry_utils.calculate_time_to_expiry_from_market_data",
            side_effect=mock_time_to_expiry,
        ):
            result = group_markets_by_expiry(markets, current)

            assert len(result) == 1
            assert 0.416 in result
            assert len(result[0.416]) == 1

    def test_use_time_buckets(self):
        """Test grouping with time buckets."""
        current = datetime(2025, 1, 1, tzinfo=timezone.utc)

        markets = [
            {"ticker": "M1", "close_time": datetime(2025, 3, 1, tzinfo=timezone.utc)},
            {"ticker": "M2", "close_time": datetime(2026, 1, 1, tzinfo=timezone.utc)},
        ]

        def mock_time_to_expiry(market, current_time):
            if market["ticker"] == "M1":
                return 0.15  # Should map to bucket 0
            return 1.0  # Should map to bucket 2

        with patch(
            "common.expiry_utils.calculate_time_to_expiry_from_market_data",
            side_effect=mock_time_to_expiry,
        ):
            result = group_markets_by_expiry(markets, current, use_time_buckets=True)

            # Check that buckets are used
            assert len(result) == 2
            assert 0.0 in result or 2.0 in result

    def test_all_markets_invalid_raises_error(self):
        """Test that if all markets are invalid, ValueError is raised."""
        current = datetime(2025, 1, 1, tzinfo=timezone.utc)

        markets = [
            {"ticker": "M1", "close_time": "invalid"},
            {"ticker": "M2", "close_time": "invalid"},
        ]

        with patch(
            "common.expiry_utils.calculate_time_to_expiry_from_market_data",
            side_effect=ValueError("Invalid"),
        ):
            with pytest.raises(ValueError, match="No valid markets found"):
                group_markets_by_expiry(markets, current)


class TestValidateExpiryGroupStrikes:
    """Tests for validate_expiry_group_strikes function."""

    def test_valid_groups_pass_validation(self):
        """Test that groups with sufficient strikes pass validation."""
        markets1 = [
            {"strike": 100},
            {"strike": 110},
            {"strike": 120},
        ]
        markets2 = [
            {"strike": 100},
            {"strike": 105},
        ]

        expiry_groups = {
            0.5: markets1,
            1.0: markets2,
        }

        with patch(
            "common.expiry_utils._extract_unique_strikes_from_markets",
            side_effect=[[100.0, 110.0, 120.0], [100.0, 105.0]],
        ):
            result = validate_expiry_group_strikes(expiry_groups, minimum_strikes=2)

            assert len(result) == 2
            assert 0.5 in result
            assert 1.0 in result

    def test_insufficient_strikes_filtered_out(self):
        """Test that groups with insufficient strikes are filtered."""
        markets1 = [
            {"strike": 100},
            {"strike": 110},
            {"strike": 120},
        ]
        markets2 = [
            {"strike": 100},
        ]

        expiry_groups = {
            0.5: markets1,
            1.0: markets2,
        }

        with patch(
            "common.expiry_utils._extract_unique_strikes_from_markets",
            side_effect=[[100.0, 110.0, 120.0], [100.0]],
        ):
            result = validate_expiry_group_strikes(expiry_groups, minimum_strikes=2)

            assert len(result) == 1
            assert 0.5 in result
            assert 1.0 not in result

    def test_no_valid_groups_raises_error(self):
        """Test that no valid groups raises ValidationError."""
        markets1 = [{"strike": 100}]
        markets2 = [{"strike": 100}]

        expiry_groups = {
            0.5: markets1,
            1.0: markets2,
        }

        with patch(
            "common.expiry_utils._extract_unique_strikes_from_markets",
            side_effect=[[100.0], [100.0]],
        ):
            with pytest.raises(ValidationError, match="No expiry groups have sufficient strikes"):
                validate_expiry_group_strikes(expiry_groups, minimum_strikes=2)


class TestExtractUniqueStrikesFromMarkets:
    """Tests for _extract_unique_strikes_from_markets function."""

    def test_extract_unique_strikes(self):
        """Test extracting unique strikes from markets."""
        markets = [
            {"strike": 100},
            {"strike": 110},
            {"strike": 100},  # Duplicate
        ]

        with patch(
            "common.expiry_utils._extract_strikes_from_market",
            side_effect=[[100.0], [110.0], [100.0]],
        ):
            result = _extract_unique_strikes_from_markets(markets)

            assert len(result) == 2
            assert 100.0 in result
            assert 110.0 in result

    def test_skip_invalid_markets(self):
        """Test that invalid markets are skipped."""
        markets = [
            {"strike": 100},
            {"strike": "invalid"},
            {"strike": 110},
        ]

        def mock_extract(market):
            if market["strike"] == "invalid":
                raise ValueError("Invalid strike")
            return [float(market["strike"])]

        with patch(
            "common.expiry_utils._extract_strikes_from_market",
            side_effect=mock_extract,
        ):
            result = _extract_unique_strikes_from_markets(markets)

            assert len(result) == 2
            assert 100.0 in result
            assert 110.0 in result


class TestExtractStrikesFromMarket:
    """Tests for _extract_strikes_from_market function."""

    def test_extract_strike_from_dict(self):
        """Test extracting strike from dict."""
        market = {"strike": 100}
        result = _extract_strikes_from_market(market)
        assert result == [100.0]

    def test_extract_floor_and_cap_strikes(self):
        """Test extracting floor and cap strikes."""
        market = {"floor_strike": 95, "cap_strike": 105}
        result = _extract_strikes_from_market(market)
        assert 95.0 in result
        assert 105.0 in result

    def test_extract_all_strike_types(self):
        """Test extracting all available strike types."""
        market = {"strike": 100, "floor_strike": 95, "cap_strike": 105}
        result = _extract_strikes_from_market(market)
        assert len(result) == 3
        assert 100.0 in result
        assert 95.0 in result
        assert 105.0 in result

    def test_skip_none_values(self):
        """Test that None values are skipped."""
        market = {"strike": 100, "floor_strike": None}
        result = _extract_strikes_from_market(market)
        assert result == [100.0]

    def test_skip_empty_string_values(self):
        """Test that empty strings are skipped."""
        market = {"strike": 100, "floor_strike": ""}
        result = _extract_strikes_from_market(market)
        assert result == [100.0]

    def test_extract_from_object_attributes(self):
        """Test extracting from object attributes."""
        market = Mock(strike=100, floor_strike=95)
        result = _extract_strikes_from_market(market)
        assert 100.0 in result
        assert 95.0 in result


class TestGetFieldValue:
    """Tests for _get_field_value function."""

    def test_get_from_object_attribute(self):
        """Test getting value from object attribute."""
        obj = Mock(strike=100)
        result = _get_field_value(obj, "strike")
        assert result == 100

    def test_get_from_dict(self):
        """Test getting value from dictionary."""
        obj = {"strike": 100}
        result = _get_field_value(obj, "strike")
        assert result == 100

    def test_missing_attribute_returns_none(self):
        """Test that missing attribute returns None."""
        obj = Mock(spec=[])
        result = _get_field_value(obj, "strike")
        assert result is None

    def test_missing_dict_key_returns_none(self):
        """Test that missing dict key returns None."""
        obj = {"other_field": 100}
        result = _get_field_value(obj, "strike")
        assert result is None
