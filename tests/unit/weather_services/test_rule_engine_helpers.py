"""Tests for weather_services.rule_engine_helpers module."""

from unittest.mock import MagicMock, patch

import pytest

from common.weather_services.rule_engine_helpers import (
    DayCodeBuilder,
    DayCodeFormatError,
    InvalidMaxTemperatureError,
    InvalidStrikeMetadataError,
    InvalidTemperatureValueError,
    MarketEvaluator,
    MarketSelectionHelper,
    MissingBetweenStrikeError,
    MissingGreaterFloorStrikeError,
    MissingMaxTemperatureError,
    StationCityMappingMissingError,
    StationMappingIndexer,
    TemperatureCoercer,
    TemperatureExtractor,
    UnsupportedTemperatureTypeError,
    WeatherRuleEngineError,
    ZoneInfoUnavailableError,
)


class TestWeatherRuleEngineError:
    """Tests for WeatherRuleEngineError base exception."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = WeatherRuleEngineError()
        assert str(error) == "Weather rule engine not configured"
        assert error.message == "Weather rule engine not configured"

    def test_custom_message(self) -> None:
        """Test custom error message."""
        error = WeatherRuleEngineError("Custom error")
        assert str(error) == "Custom error"
        assert error.message == "Custom error"


class TestStationCityMappingMissingError:
    """Tests for StationCityMappingMissingError."""

    def test_includes_station_icao(self) -> None:
        """Test error includes station ICAO."""
        error = StationCityMappingMissingError("KMIA")
        assert "KMIA" in str(error)
        assert "No city mapping found" in str(error)


class TestZoneInfoUnavailableError:
    """Tests for ZoneInfoUnavailableError."""

    def test_includes_zone_name(self) -> None:
        """Test error includes zone name."""
        error = ZoneInfoUnavailableError("America/New_York")
        assert "America/New_York" in str(error)


class TestDayCodeFormatError:
    """Tests for DayCodeFormatError."""

    def test_error_message(self) -> None:
        """Test error has appropriate message."""
        error = DayCodeFormatError()
        assert "Failed to format weather day code" in str(error)


class TestInvalidTemperatureValueError:
    """Tests for InvalidTemperatureValueError."""

    def test_includes_raw_value(self) -> None:
        """Test error includes raw value."""
        error = InvalidTemperatureValueError("not_a_number")
        assert "not_a_number" in str(error)


class TestUnsupportedTemperatureTypeError:
    """Tests for UnsupportedTemperatureTypeError."""

    def test_includes_type(self) -> None:
        """Test error includes type."""
        error = UnsupportedTemperatureTypeError(list)
        assert "list" in str(error)


class TestInvalidMaxTemperatureError:
    """Tests for InvalidMaxTemperatureError."""

    def test_includes_station_icao(self) -> None:
        """Test error includes station ICAO."""
        error = InvalidMaxTemperatureError("KJFK")
        assert "KJFK" in str(error)


class TestMissingMaxTemperatureError:
    """Tests for MissingMaxTemperatureError."""

    def test_includes_station_icao(self) -> None:
        """Test error includes station ICAO."""
        error = MissingMaxTemperatureError("KORD")
        assert "KORD" in str(error)
        assert "Missing required max_temp_f" in str(error)


class TestInvalidStrikeMetadataError:
    """Tests for InvalidStrikeMetadataError."""

    def test_includes_market_key(self) -> None:
        """Test error includes market key."""
        error = InvalidStrikeMetadataError("KXMIA-25JAN01")
        assert "KXMIA-25JAN01" in str(error)


class TestMissingGreaterFloorStrikeError:
    """Tests for MissingGreaterFloorStrikeError."""

    def test_includes_market_key(self) -> None:
        """Test error includes market key."""
        error = MissingGreaterFloorStrikeError("KXMIA-25JAN01")
        assert "KXMIA-25JAN01" in str(error)
        assert "greater" in str(error)


class TestMissingBetweenStrikeError:
    """Tests for MissingBetweenStrikeError."""

    def test_includes_market_key(self) -> None:
        """Test error includes market key."""
        error = MissingBetweenStrikeError("KXMIA-25JAN01")
        assert "KXMIA-25JAN01" in str(error)
        assert "between" in str(error)


class TestTemperatureCoercer:
    """Tests for TemperatureCoercer class."""

    def test_coerce_none_returns_none(self) -> None:
        """Test None returns None."""
        assert TemperatureCoercer.coerce(None) is None

    def test_coerce_int_returns_float(self) -> None:
        """Test int is converted to float."""
        assert TemperatureCoercer.coerce(75) == 75.0
        assert isinstance(TemperatureCoercer.coerce(75), float)

    def test_coerce_float_returns_float(self) -> None:
        """Test float is returned as is."""
        assert TemperatureCoercer.coerce(75.5) == 75.5

    def test_coerce_valid_string(self) -> None:
        """Test valid string is parsed."""
        assert TemperatureCoercer.coerce("75.5") == 75.5

    def test_coerce_string_with_whitespace(self) -> None:
        """Test string with whitespace is trimmed."""
        assert TemperatureCoercer.coerce("  75.5  ") == 75.5

    def test_coerce_empty_string_returns_none(self) -> None:
        """Test empty string returns None."""
        assert TemperatureCoercer.coerce("") is None

    def test_coerce_none_string_returns_none(self) -> None:
        """Test 'none' string returns None."""
        assert TemperatureCoercer.coerce("none") is None
        assert TemperatureCoercer.coerce("None") is None

    def test_coerce_invalid_string_raises(self) -> None:
        """Test invalid string raises InvalidTemperatureValueError."""
        with pytest.raises(InvalidTemperatureValueError):
            TemperatureCoercer.coerce("not_a_number")

    def test_coerce_unsupported_type_raises(self) -> None:
        """Test unsupported type raises UnsupportedTemperatureTypeError."""
        with pytest.raises(UnsupportedTemperatureTypeError):
            TemperatureCoercer.coerce([75])


class TestDayCodeBuilder:
    """Tests for DayCodeBuilder class."""

    def test_build_returns_valid_format(self) -> None:
        """Test build returns valid day code format."""
        result = DayCodeBuilder.build()

        # Format: YYMMMDD (e.g., 25JAN01)
        assert len(result) == 7
        assert result[:2].isdigit()  # Year
        assert result[2:5].isalpha()  # Month
        assert result[5:].isdigit()  # Day

    def test_build_with_zoneinfo_error(self) -> None:
        """Test handles ZoneInfo not found."""
        with patch(
            "common.weather_services.rule_engine_helpers.ZoneInfo",
            side_effect=Exception("Not found"),
        ):
            # The original code catches ZoneInfoNotFoundError
            with patch(
                "common.weather_services.rule_engine_helpers.ZoneInfoNotFoundError",
                Exception,
            ):
                with pytest.raises(Exception):
                    DayCodeBuilder.build()


class TestStationMappingIndexer:
    """Tests for StationMappingIndexer class."""

    def test_build_alias_index_empty_mapping(self) -> None:
        """Test building index from empty mapping."""
        result = StationMappingIndexer.build_alias_index({})
        assert result == {}

    def test_build_alias_index_with_aliases(self) -> None:
        """Test building index with aliases."""
        mapping = {
            "miami": {"icao": "KMIA", "aliases": ["MIA", "MIAMI"]},
            "new_york": {"icao": "KJFK", "aliases": ["JFK", "NYC"]},
        }

        result = StationMappingIndexer.build_alias_index(mapping)

        assert result["MIA"] == "miami"
        assert result["MIAMI"] == "miami"
        assert result["JFK"] == "new_york"
        assert result["NYC"] == "new_york"

    def test_build_alias_index_no_aliases(self) -> None:
        """Test building index with no aliases."""
        mapping = {"miami": {"icao": "KMIA"}}

        result = StationMappingIndexer.build_alias_index(mapping)

        assert result == {}

    def test_resolve_city_code_direct_match(self) -> None:
        """Test resolving city code by direct ICAO match."""
        mapping = {"miami": {"icao": "KMIA"}}
        alias_index: dict[str, str] = {}

        result = StationMappingIndexer.resolve_city_code("KMIA", mapping, alias_index)

        assert result == "miami"

    def test_resolve_city_code_alias_match(self) -> None:
        """Test resolving city code by alias match."""
        mapping = {"miami": {"icao": "KMIA", "aliases": ["MIA"]}}
        alias_index = {"MIA": "miami"}

        result = StationMappingIndexer.resolve_city_code("MIA", mapping, alias_index)

        assert result == "miami"

    def test_resolve_city_code_no_match(self) -> None:
        """Test resolving city code with no match."""
        mapping = {"miami": {"icao": "KMIA"}}
        alias_index: dict[str, str] = {}

        result = StationMappingIndexer.resolve_city_code("KJFK", mapping, alias_index)

        assert result is None


class TestTemperatureExtractor:
    """Tests for TemperatureExtractor class."""

    def test_extract_max_temp_valid(self) -> None:
        """Test extracting valid max temp."""
        weather_data = {"max_temp_f": 75.5}

        result = TemperatureExtractor.extract_max_temp(weather_data, "KMIA")

        assert result == 75.5

    def test_extract_max_temp_from_string(self) -> None:
        """Test extracting max temp from string."""
        weather_data = {"max_temp_f": "82"}

        result = TemperatureExtractor.extract_max_temp(weather_data, "KMIA")

        assert result == 82.0

    def test_extract_max_temp_missing_raises(self) -> None:
        """Test missing max temp raises error."""
        weather_data: dict[str, float | None] = {"max_temp_f": None}

        with pytest.raises(MissingMaxTemperatureError):
            TemperatureExtractor.extract_max_temp(weather_data, "KMIA")

    def test_extract_max_temp_invalid_raises(self) -> None:
        """Test invalid max temp raises error."""
        weather_data = {"max_temp_f": "invalid"}

        with pytest.raises(InvalidMaxTemperatureError):
            TemperatureExtractor.extract_max_temp(weather_data, "KMIA")


class TestMarketSelectionHelper:
    """Tests for MarketSelectionHelper class."""

    def test_is_temperature_in_band_within(self) -> None:
        """Test temperature within band."""
        assert MarketSelectionHelper.is_temperature_in_band(75.0, 70.0, 80.0) is True

    def test_is_temperature_in_band_at_floor(self) -> None:
        """Test temperature at floor."""
        assert MarketSelectionHelper.is_temperature_in_band(70.0, 70.0, 80.0) is True

    def test_is_temperature_in_band_at_cap(self) -> None:
        """Test temperature at cap."""
        assert MarketSelectionHelper.is_temperature_in_band(80.0, 70.0, 80.0) is True

    def test_is_temperature_in_band_below(self) -> None:
        """Test temperature below band."""
        assert MarketSelectionHelper.is_temperature_in_band(65.0, 70.0, 80.0) is False

    def test_is_temperature_in_band_above(self) -> None:
        """Test temperature above band."""
        assert MarketSelectionHelper.is_temperature_in_band(85.0, 70.0, 80.0) is False

    def test_is_temperature_in_band_none_floor(self) -> None:
        """Test returns False when floor is None."""
        assert MarketSelectionHelper.is_temperature_in_band(75.0, None, 80.0) is False

    def test_is_temperature_in_band_none_cap(self) -> None:
        """Test returns False when cap is None."""
        assert MarketSelectionHelper.is_temperature_in_band(75.0, 70.0, None) is False

    def test_calculate_market_width_valid(self) -> None:
        """Test calculating market width."""
        assert MarketSelectionHelper.calculate_market_width(70.0, 80.0) == 10.0

    def test_calculate_market_width_none_floor(self) -> None:
        """Test returns None when floor is None."""
        assert MarketSelectionHelper.calculate_market_width(None, 80.0) is None

    def test_calculate_market_width_none_cap(self) -> None:
        """Test returns None when cap is None."""
        assert MarketSelectionHelper.calculate_market_width(70.0, None) is None


class TestMarketEvaluator:
    """Tests for MarketEvaluator class."""

    def test_extract_strike_values_valid(self) -> None:
        """Test extracting valid strike values."""
        mock_snapshot = MagicMock()
        mock_snapshot.data = {"cap_strike": "80.0", "floor_strike": "70.0"}

        cap, floor = MarketEvaluator.extract_strike_values(mock_snapshot, TemperatureCoercer)

        assert cap == 80.0
        assert floor == 70.0

    def test_extract_strike_values_invalid_raises(self) -> None:
        """Test invalid strike values raise error."""
        mock_snapshot = MagicMock()
        mock_snapshot.data = {"cap_strike": "invalid", "floor_strike": "70.0"}
        mock_snapshot.key = "test_market"

        with pytest.raises(InvalidStrikeMetadataError):
            MarketEvaluator.extract_strike_values(mock_snapshot, TemperatureCoercer)

    def test_evaluate_greater_market_qualifies(self) -> None:
        """Test greater market qualifies."""
        mock_snapshot = MagicMock()
        mock_snapshot.key = "test_market"

        result = MarketEvaluator.evaluate_greater_market(
            max_temp_f=75.0,
            floor=70.0,
            snapshot=mock_snapshot,
            best_floor=None,
        )

        assert result is True

    def test_evaluate_greater_market_below_floor(self) -> None:
        """Test greater market below floor."""
        mock_snapshot = MagicMock()
        mock_snapshot.key = "test_market"

        result = MarketEvaluator.evaluate_greater_market(
            max_temp_f=65.0,
            floor=70.0,
            snapshot=mock_snapshot,
            best_floor=None,
        )

        assert result is False

    def test_evaluate_greater_market_better_floor(self) -> None:
        """Test greater market with better floor."""
        mock_snapshot = MagicMock()
        mock_snapshot.key = "test_market"

        result = MarketEvaluator.evaluate_greater_market(
            max_temp_f=75.0,
            floor=72.0,
            snapshot=mock_snapshot,
            best_floor=70.0,
        )

        assert result is True

    def test_evaluate_greater_market_worse_floor(self) -> None:
        """Test greater market with worse floor."""
        mock_snapshot = MagicMock()
        mock_snapshot.key = "test_market"

        result = MarketEvaluator.evaluate_greater_market(
            max_temp_f=75.0,
            floor=68.0,
            snapshot=mock_snapshot,
            best_floor=70.0,
        )

        assert result is False

    def test_evaluate_greater_market_none_floor_raises(self) -> None:
        """Test greater market with None floor raises."""
        mock_snapshot = MagicMock()
        mock_snapshot.key = "test_market"

        with pytest.raises(MissingGreaterFloorStrikeError):
            MarketEvaluator.evaluate_greater_market(
                max_temp_f=75.0,
                floor=None,
                snapshot=mock_snapshot,
                best_floor=None,
            )

    def test_evaluate_between_market_in_band(self) -> None:
        """Test between market in band."""
        mock_snapshot = MagicMock()
        mock_snapshot.key = "test_market"

        selected, selected_cap, selected_floor = MarketEvaluator.evaluate_between_market(
            max_temp_f=75.0,
            cap=80.0,
            floor=70.0,
            snapshot=mock_snapshot,
            best_snapshot=None,
            best_cap=None,
            best_floor=None,
        )

        assert selected == mock_snapshot
        assert selected_cap == 80.0
        assert selected_floor == 70.0

    def test_evaluate_between_market_out_of_band(self) -> None:
        """Test between market out of band."""
        mock_snapshot = MagicMock()
        mock_snapshot.key = "test_market"
        mock_best = MagicMock()

        selected, selected_cap, selected_floor = MarketEvaluator.evaluate_between_market(
            max_temp_f=85.0,
            cap=80.0,
            floor=70.0,
            snapshot=mock_snapshot,
            best_snapshot=mock_best,
            best_cap=90.0,
            best_floor=80.0,
        )

        assert selected == mock_best
        assert selected_cap == 90.0
        assert selected_floor == 80.0

    def test_evaluate_between_market_narrower_band_wins(self) -> None:
        """Test narrower band wins."""
        mock_snapshot = MagicMock()
        mock_snapshot.key = "current"
        mock_best = MagicMock()
        mock_best.key = "best"

        # Current band: 70-80 (width 10)
        # Best band: 68-82 (width 14)
        # Current is narrower, so it should win
        selected, selected_cap, selected_floor = MarketEvaluator.evaluate_between_market(
            max_temp_f=75.0,
            cap=80.0,
            floor=70.0,
            snapshot=mock_snapshot,
            best_snapshot=mock_best,
            best_cap=82.0,
            best_floor=68.0,
        )

        assert selected == mock_snapshot
        assert selected_cap == 80.0
        assert selected_floor == 70.0

    def test_evaluate_between_market_none_cap_raises(self) -> None:
        """Test None cap raises error."""
        mock_snapshot = MagicMock()
        mock_snapshot.key = "test_market"

        with pytest.raises(MissingBetweenStrikeError):
            MarketEvaluator.evaluate_between_market(
                max_temp_f=75.0,
                cap=None,
                floor=70.0,
                snapshot=mock_snapshot,
                best_snapshot=None,
                best_cap=None,
                best_floor=None,
            )

    def test_evaluate_between_market_none_floor_raises(self) -> None:
        """Test None floor raises error."""
        mock_snapshot = MagicMock()
        mock_snapshot.key = "test_market"

        with pytest.raises(MissingBetweenStrikeError):
            MarketEvaluator.evaluate_between_market(
                max_temp_f=75.0,
                cap=80.0,
                floor=None,
                snapshot=mock_snapshot,
                best_snapshot=None,
                best_cap=None,
                best_floor=None,
            )
