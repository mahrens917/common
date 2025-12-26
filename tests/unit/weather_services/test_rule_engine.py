"""Tests for weather_services.rule_engine module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.weather_services.rule_engine import (
    MidpointSignalResult,
    WeatherRuleEngine,
)
from common.weather_services.rule_engine_helpers import (
    StationCityMappingMissingError,
    WeatherRuleEngineError,
)


class TestMidpointSignalResult:
    """Tests for MidpointSignalResult dataclass."""

    def test_stores_all_fields(self) -> None:
        """Test stores all fields."""
        result = MidpointSignalResult(
            station_icao="KMIA",
            market_key="kalshi:weather:KMIA",
            ticker="KXHIGHMIA-25DEC26-T72",
            max_temp_f=75.5,
            explanation="Test explanation",
        )

        assert result.station_icao == "KMIA"
        assert result.market_key == "kalshi:weather:KMIA"
        assert result.ticker == "KXHIGHMIA-25DEC26-T72"
        assert result.max_temp_f == 75.5
        assert result.explanation == "Test explanation"

    def test_is_frozen(self) -> None:
        """Test dataclass is frozen."""
        result = MidpointSignalResult(
            station_icao="KMIA",
            market_key="key",
            ticker="ticker",
            max_temp_f=70.0,
            explanation="exp",
        )

        with pytest.raises(AttributeError):
            result.station_icao = "KJFK"


class TestWeatherRuleEngineInit:
    """Tests for WeatherRuleEngine initialization."""

    def test_stores_repository(self) -> None:
        """Test stores repository."""
        mock_repo = MagicMock()
        mock_loader = MagicMock(return_value={"KMIA": {"city_code": "MIA"}})

        with patch("common.weather_services.rule_engine.StationMappingIndexer.build_alias_index", return_value={}):
            engine = WeatherRuleEngine(mock_repo, station_mapping_loader=mock_loader)

            assert engine._repository is mock_repo

    def test_loads_station_mapping(self) -> None:
        """Test loads station mapping on init."""
        mock_repo = MagicMock()
        mock_loader = MagicMock(return_value={"KMIA": {"city_code": "MIA"}})

        with patch("common.weather_services.rule_engine.StationMappingIndexer.build_alias_index", return_value={}):
            engine = WeatherRuleEngine(mock_repo, station_mapping_loader=mock_loader)

            mock_loader.assert_called_once()
            assert engine._station_mapping == {"KMIA": {"city_code": "MIA"}}

    def test_builds_alias_index(self) -> None:
        """Test builds alias index from station mapping."""
        mock_repo = MagicMock()
        mock_loader = MagicMock(return_value={"KMIA": {"city_code": "MIA"}})

        with patch("common.weather_services.rule_engine.StationMappingIndexer.build_alias_index") as mock_build:
            mock_build.return_value = {"MIA": "KMIA"}
            engine = WeatherRuleEngine(mock_repo, station_mapping_loader=mock_loader)

            mock_build.assert_called_once_with({"KMIA": {"city_code": "MIA"}})
            assert engine._alias_index == {"MIA": "KMIA"}

    def test_raises_on_config_error(self) -> None:
        """Test raises WeatherRuleEngineError on config error."""
        from common.config.weather import WeatherConfigError

        mock_repo = MagicMock()
        mock_loader = MagicMock(side_effect=WeatherConfigError("Config error"))

        with pytest.raises(WeatherRuleEngineError) as exc_info:
            WeatherRuleEngine(mock_repo, station_mapping_loader=mock_loader)

        assert "Config error" in str(exc_info.value)


class TestWeatherRuleEngineApplyMidpointSignal:
    """Tests for apply_midpoint_signal method."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_weather_data(self) -> None:
        """Test returns None when no weather data available."""
        mock_repo = MagicMock()
        mock_repo.get_weather_data = AsyncMock(return_value=None)
        mock_loader = MagicMock(return_value={})

        with patch("common.weather_services.rule_engine.StationMappingIndexer.build_alias_index", return_value={}):
            engine = WeatherRuleEngine(mock_repo, station_mapping_loader=mock_loader)
            result = await engine.apply_midpoint_signal("KMIA")

            assert result is None

    @pytest.mark.asyncio
    async def test_raises_when_city_code_not_found(self) -> None:
        """Test raises StationCityMappingMissingError when city code not found."""
        mock_repo = MagicMock()
        mock_repo.get_weather_data = AsyncMock(return_value={"temp_f": 75.0})
        mock_loader = MagicMock(return_value={})

        with patch("common.weather_services.rule_engine.StationMappingIndexer.build_alias_index", return_value={}):
            with patch("common.weather_services.rule_engine.TemperatureExtractor.extract_max_temp", return_value=75.0):
                with patch("common.weather_services.rule_engine.StationMappingIndexer.resolve_city_code", return_value=None):
                    engine = WeatherRuleEngine(mock_repo, station_mapping_loader=mock_loader)

                    with pytest.raises(StationCityMappingMissingError):
                        await engine.apply_midpoint_signal("KMIA")

    @pytest.mark.asyncio
    async def test_returns_none_when_no_target_market(self) -> None:
        """Test returns None when no target market found."""
        mock_repo = MagicMock()
        mock_repo.get_weather_data = AsyncMock(return_value={"temp_f": 75.0})

        async def empty_iter(*_args, **_kwargs):
            for _ in []:
                yield

        mock_repo.iter_city_markets = empty_iter
        mock_loader = MagicMock(return_value={"KMIA": {"city_code": "MIA"}})

        with patch("common.weather_services.rule_engine.StationMappingIndexer.build_alias_index", return_value={}):
            with patch("common.weather_services.rule_engine.TemperatureExtractor.extract_max_temp", return_value=75.0):
                with patch("common.weather_services.rule_engine.StationMappingIndexer.resolve_city_code", return_value="MIA"):
                    with patch("common.weather_services.rule_engine.DayCodeBuilder.build", return_value="25DEC26"):
                        engine = WeatherRuleEngine(mock_repo, station_mapping_loader=mock_loader)
                        result = await engine.apply_midpoint_signal("KMIA")

                        assert result is None

    @pytest.mark.asyncio
    async def test_returns_result_when_market_found(self) -> None:
        """Test returns MidpointSignalResult when target market found."""
        mock_repo = MagicMock()
        mock_repo.get_weather_data = AsyncMock(return_value={"temp_f": 75.0})
        mock_repo.set_market_fields = AsyncMock()

        mock_snapshot = MagicMock()
        mock_snapshot.key = "kalshi:weather:MIA"
        mock_snapshot.ticker = "KXHIGHMIA-25DEC26-T75"
        mock_snapshot.strike_type = "greater"
        mock_snapshot.data = {"floor": 74}

        async def market_iter(*_args, **_kwargs):
            yield mock_snapshot

        mock_repo.iter_city_markets = market_iter
        mock_loader = MagicMock(return_value={"KMIA": {"city_code": "MIA"}})

        with patch("common.weather_services.rule_engine.StationMappingIndexer.build_alias_index", return_value={}):
            with patch("common.weather_services.rule_engine.TemperatureExtractor.extract_max_temp", return_value=75.0):
                with patch("common.weather_services.rule_engine.StationMappingIndexer.resolve_city_code", return_value="MIA"):
                    with patch("common.weather_services.rule_engine.DayCodeBuilder.build", return_value="25DEC26"):
                        with patch("common.weather_services.rule_engine.MarketEvaluator.extract_strike_values", return_value=(None, 74)):
                            with patch("common.weather_services.rule_engine.MarketEvaluator.evaluate_greater_market", return_value=True):
                                engine = WeatherRuleEngine(mock_repo, station_mapping_loader=mock_loader)
                                result = await engine.apply_midpoint_signal("KMIA")

                                assert result is not None
                                assert isinstance(result, MidpointSignalResult)
                                assert result.station_icao == "KMIA"
                                assert result.max_temp_f == 75.0


class TestWeatherRuleEngineReloadStationMapping:
    """Tests for reload_station_mapping method."""

    def test_reloads_mapping(self) -> None:
        """Test reloads station mapping."""
        mock_repo = MagicMock()
        call_count = [0]

        def loader():
            call_count[0] += 1
            return {"KMIA": {"city_code": "MIA", "version": call_count[0]}}

        with patch("common.weather_services.rule_engine.StationMappingIndexer.build_alias_index", return_value={}):
            engine = WeatherRuleEngine(mock_repo, station_mapping_loader=loader)
            assert engine._station_mapping["KMIA"]["version"] == 1

            engine.reload_station_mapping()
            assert engine._station_mapping["KMIA"]["version"] == 2

    def test_rebuilds_alias_index(self) -> None:
        """Test rebuilds alias index on reload."""
        mock_repo = MagicMock()
        mock_loader = MagicMock(return_value={"KMIA": {"city_code": "MIA"}})

        with patch("common.weather_services.rule_engine.StationMappingIndexer.build_alias_index") as mock_build:
            mock_build.return_value = {}
            engine = WeatherRuleEngine(mock_repo, station_mapping_loader=mock_loader)

            mock_build.reset_mock()
            engine.reload_station_mapping()

            mock_build.assert_called_once()


class TestWeatherRuleEngineCoerceTemperature:
    """Tests for _coerce_temperature static method."""

    def test_coerces_valid_temperature(self) -> None:
        """Test coerces valid temperature value."""
        with patch("common.weather_services.rule_engine.TemperatureCoercer.coerce", return_value=75.5):
            result = WeatherRuleEngine._coerce_temperature("75.5")
            assert result == 75.5

    def test_raises_value_error_on_invalid(self) -> None:
        """Test raises ValueError on invalid temperature."""
        from common.weather_services.rule_engine_helpers import InvalidTemperatureValueError

        with patch("common.weather_services.rule_engine.TemperatureCoercer.coerce") as mock_coerce:
            mock_coerce.side_effect = InvalidTemperatureValueError("Invalid")

            with pytest.raises(ValueError):
                WeatherRuleEngine._coerce_temperature("invalid")

    def test_raises_value_error_on_unsupported_type(self) -> None:
        """Test raises ValueError on unsupported temperature type."""
        from common.weather_services.rule_engine_helpers import UnsupportedTemperatureTypeError

        with patch("common.weather_services.rule_engine.TemperatureCoercer.coerce") as mock_coerce:
            mock_coerce.side_effect = UnsupportedTemperatureTypeError("Unsupported")

            with pytest.raises(ValueError):
                WeatherRuleEngine._coerce_temperature([1, 2, 3])
