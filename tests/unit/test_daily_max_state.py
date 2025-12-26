"""Tests for DailyMaxState class."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from common.daily_max_state import DailyMaxState, MetarConfigLoadError, create_daily_max_state

TEST_TEMP_C_25 = 25.0
TEST_TEMP_C_30 = 30.0
TEST_MAX_TEMP_INT_28 = 28
TEST_TIMESTAMP_1234567890 = 1234567890
TEST_PRECISION_0_1 = 0.1
TEST_PRECISION_1_0 = 1.0
TEST_SOURCE_METAR = "metar"
TEST_SOURCE_HOURLY = "hourly"
TEST_CONFIDENCE_HIGH = "HIGH"
TEST_CONFIDENCE_MEDIUM = "MEDIUM"
TEST_MARGIN_0_5 = 0.5
TEST_MARGIN_1_0 = 1.0
TEST_TEMP_F_86 = 86
TEST_TEMP_F_77 = 77
TEST_RULE_TYPE_4 = "4"
TEST_RULE_TYPE_7 = "7"


@pytest.fixture
def mock_metar_config() -> Dict[str, Any]:
    """Fixture for mock METAR config."""
    return {
        "precision": TEST_PRECISION_0_1,
        "data_source": "test_metar",
    }


@pytest.fixture
def daily_max_state(mock_metar_config: Dict[str, Any]) -> DailyMaxState:
    """Fixture to create DailyMaxState instance with mocked config."""
    with patch("common.daily_max_state.DailyMaxStateFactory.create_metar_config") as mock_config:
        mock_config.return_value = mock_metar_config
        return DailyMaxState()


class TestDailyMaxStateInit:
    """Tests for DailyMaxState initialization."""

    def test_init_creates_initial_state(self, daily_max_state: DailyMaxState) -> None:
        """__init__ creates initial state with default values."""
        assert daily_max_state.max_temp_c == float("-inf")
        assert daily_max_state.precision is None
        assert daily_max_state.source is None
        assert daily_max_state.timestamp is None
        assert daily_max_state.hourly_max_temp_c == float("-inf")
        assert daily_max_state.hourly_timestamp is None

    def test_init_loads_metar_config(self, daily_max_state: DailyMaxState) -> None:
        """__init__ loads METAR configuration."""
        assert daily_max_state.metar_config is not None
        assert "precision" in daily_max_state.metar_config

    def test_init_raises_on_config_load_error(self) -> None:
        """__init__ raises MetarConfigLoadError when config loading fails."""
        with patch("common.daily_max_state.DailyMaxStateFactory.create_metar_config") as mock_config:
            mock_config.side_effect = MetarConfigLoadError("Config load failed")
            with pytest.raises(MetarConfigLoadError, match="Config load failed"):
                DailyMaxState()


class TestDailyMaxStateGetAttr:
    """Tests for DailyMaxState __getattr__ method."""

    def test_getattr_returns_state_field(self, daily_max_state: DailyMaxState) -> None:
        """__getattr__ returns value from state for valid field."""
        daily_max_state.max_temp_c = TEST_TEMP_C_25
        assert daily_max_state.max_temp_c == TEST_TEMP_C_25

    def test_getattr_returns_precision(self, daily_max_state: DailyMaxState) -> None:
        """__getattr__ returns precision field."""
        daily_max_state.precision = TEST_PRECISION_0_1
        assert daily_max_state.precision == TEST_PRECISION_0_1

    def test_getattr_returns_source(self, daily_max_state: DailyMaxState) -> None:
        """__getattr__ returns source field."""
        daily_max_state.source = TEST_SOURCE_METAR
        assert daily_max_state.source == TEST_SOURCE_METAR

    def test_getattr_returns_timestamp(self, daily_max_state: DailyMaxState) -> None:
        """__getattr__ returns timestamp field."""
        daily_max_state.timestamp = TEST_TIMESTAMP_1234567890
        assert daily_max_state.timestamp == TEST_TIMESTAMP_1234567890

    def test_getattr_returns_hourly_max_temp_c(self, daily_max_state: DailyMaxState) -> None:
        """__getattr__ returns hourly_max_temp_c field."""
        daily_max_state.hourly_max_temp_c = TEST_TEMP_C_30
        assert daily_max_state.hourly_max_temp_c == TEST_TEMP_C_30

    def test_getattr_returns_hourly_timestamp(self, daily_max_state: DailyMaxState) -> None:
        """__getattr__ returns hourly_timestamp field."""
        daily_max_state.hourly_timestamp = TEST_TIMESTAMP_1234567890
        assert daily_max_state.hourly_timestamp == TEST_TIMESTAMP_1234567890

    def test_getattr_returns_metar_config(self, daily_max_state: DailyMaxState) -> None:
        """__getattr__ returns metar_config."""
        assert daily_max_state.metar_config is not None

    def test_getattr_raises_for_unknown_attribute(self, daily_max_state: DailyMaxState) -> None:
        """__getattr__ raises AttributeError for unknown attribute."""
        with pytest.raises(AttributeError, match="unknown_attr"):
            _ = daily_max_state.unknown_attr


class TestDailyMaxStateSetAttr:
    """Tests for DailyMaxState __setattr__ method."""

    def test_setattr_sets_state_field(self, daily_max_state: DailyMaxState) -> None:
        """__setattr__ sets value in state for valid field."""
        daily_max_state.max_temp_c = TEST_TEMP_C_30
        assert daily_max_state.max_temp_c == TEST_TEMP_C_30

    def test_setattr_sets_precision(self, daily_max_state: DailyMaxState) -> None:
        """__setattr__ sets precision field."""
        daily_max_state.precision = TEST_PRECISION_1_0
        assert daily_max_state.precision == TEST_PRECISION_1_0

    def test_setattr_sets_source(self, daily_max_state: DailyMaxState) -> None:
        """__setattr__ sets source field."""
        daily_max_state.source = TEST_SOURCE_HOURLY
        assert daily_max_state.source == TEST_SOURCE_HOURLY

    def test_setattr_sets_timestamp(self, daily_max_state: DailyMaxState) -> None:
        """__setattr__ sets timestamp field."""
        daily_max_state.timestamp = TEST_TIMESTAMP_1234567890
        assert daily_max_state.timestamp == TEST_TIMESTAMP_1234567890

    def test_setattr_sets_hourly_max_temp_c(self, daily_max_state: DailyMaxState) -> None:
        """__setattr__ sets hourly_max_temp_c field."""
        daily_max_state.hourly_max_temp_c = TEST_TEMP_C_25
        assert daily_max_state.hourly_max_temp_c == TEST_TEMP_C_25

    def test_setattr_sets_hourly_timestamp(self, daily_max_state: DailyMaxState) -> None:
        """__setattr__ sets hourly_timestamp field."""
        daily_max_state.hourly_timestamp = TEST_TIMESTAMP_1234567890
        assert daily_max_state.hourly_timestamp == TEST_TIMESTAMP_1234567890

    def test_setattr_allows_slots_attributes(self, daily_max_state: DailyMaxState) -> None:
        """__setattr__ allows setting __slots__ attributes."""
        mock_state = {"max_temp_c": None}
        daily_max_state._state = mock_state
        assert daily_max_state._state == mock_state


class TestDailyMaxStateAddHourlyObservation:
    """Tests for add_hourly_observation method."""

    def test_add_hourly_observation_delegates_to_delegator(self, daily_max_state: DailyMaxState) -> None:
        """add_hourly_observation delegates to ObservationTracker."""
        mock_timestamp = datetime.now()
        with patch.object(daily_max_state._delegator, "add_hourly_observation") as mock_add:
            daily_max_state.add_hourly_observation(TEST_TEMP_C_25, mock_timestamp)
            mock_add.assert_called_once_with(TEST_TEMP_C_25, mock_timestamp)

    def test_add_hourly_observation_with_none_timestamp(self, daily_max_state: DailyMaxState) -> None:
        """add_hourly_observation works with None timestamp."""
        with patch.object(daily_max_state._delegator, "add_hourly_observation") as mock_add:
            daily_max_state.add_hourly_observation(TEST_TEMP_C_30, None)
            mock_add.assert_called_once_with(TEST_TEMP_C_30, None)


class TestDailyMaxStateAdd6hMaximum:
    """Tests for add_6h_maximum method."""

    def test_add_6h_maximum_delegates_to_delegator(self, daily_max_state: DailyMaxState) -> None:
        """add_6h_maximum delegates to ObservationTracker."""
        mock_window_end = datetime.now()
        with patch.object(daily_max_state._delegator, "add_6h_maximum") as mock_add:
            daily_max_state.add_6h_maximum(TEST_MAX_TEMP_INT_28, mock_window_end)
            mock_add.assert_called_once_with(TEST_MAX_TEMP_INT_28, mock_window_end)

    def test_add_6h_maximum_with_none_window_end(self, daily_max_state: DailyMaxState) -> None:
        """add_6h_maximum works with None window_end."""
        with patch.object(daily_max_state._delegator, "add_6h_maximum") as mock_add:
            daily_max_state.add_6h_maximum(TEST_MAX_TEMP_INT_28, None)
            mock_add.assert_called_once_with(TEST_MAX_TEMP_INT_28, None)


class TestDailyMaxStateGetConfidenceLevel:
    """Tests for get_confidence_level method."""

    def test_get_confidence_level_delegates_to_delegator(self, daily_max_state: DailyMaxState) -> None:
        """get_confidence_level delegates to ConfidenceCalculator."""
        with patch.object(daily_max_state._delegator, "get_confidence_level") as mock_get:
            mock_get.return_value = TEST_CONFIDENCE_HIGH
            result = daily_max_state.get_confidence_level()
            assert result == TEST_CONFIDENCE_HIGH
            mock_get.assert_called_once()


class TestDailyMaxStateGetSafetyMarginC:
    """Tests for get_safety_margin_c method."""

    def test_get_safety_margin_c_delegates_to_delegator(self, daily_max_state: DailyMaxState) -> None:
        """get_safety_margin_c delegates to ConfidenceCalculator."""
        with patch.object(daily_max_state._delegator, "get_safety_margin_c") as mock_get:
            mock_get.return_value = TEST_MARGIN_0_5
            result = daily_max_state.get_safety_margin_c()
            assert result == TEST_MARGIN_0_5
            mock_get.assert_called_once()


class TestDailyMaxStateGetDailyMaxResult:
    """Tests for get_daily_max_result method."""

    def test_get_daily_max_result_delegates_to_delegator(self, daily_max_state: DailyMaxState) -> None:
        """get_daily_max_result delegates to ResultGenerator."""
        mock_result = MagicMock()
        with patch.object(daily_max_state._delegator, "get_daily_max_result") as mock_get:
            mock_get.return_value = mock_result
            result = daily_max_state.get_daily_max_result()
            assert result == mock_result
            mock_get.assert_called_once()


class TestDailyMaxStateGetAdjustedTempForRule:
    """Tests for get_adjusted_temp_for_rule method."""

    def test_get_adjusted_temp_for_rule_delegates_to_delegator(self, daily_max_state: DailyMaxState) -> None:
        """get_adjusted_temp_for_rule delegates to ResultGenerator."""
        with patch.object(daily_max_state._delegator, "get_adjusted_temp_for_rule") as mock_get:
            mock_get.return_value = TEST_TEMP_F_86
            result = daily_max_state.get_adjusted_temp_for_rule(TEST_RULE_TYPE_4)
            assert result == TEST_TEMP_F_86
            mock_get.assert_called_once_with(TEST_RULE_TYPE_4)


class TestDailyMaxStateGetHourlyOnlyMaxF:
    """Tests for get_hourly_only_max_f method."""

    def test_get_hourly_only_max_f_delegates_to_delegator(self, daily_max_state: DailyMaxState) -> None:
        """get_hourly_only_max_f delegates to ResultGenerator."""
        with patch.object(daily_max_state._delegator, "get_hourly_only_max_f") as mock_get:
            mock_get.return_value = TEST_TEMP_F_77
            result = daily_max_state.get_hourly_only_max_f()
            assert result == TEST_TEMP_F_77
            mock_get.assert_called_once()


class TestDailyMaxStateResetForNewDay:
    """Tests for reset_for_new_day method."""

    def test_reset_for_new_day_delegates_to_delegator(self, daily_max_state: DailyMaxState) -> None:
        """reset_for_new_day delegates to StateManager."""
        with patch.object(daily_max_state._delegator, "reset_for_new_day") as mock_reset:
            daily_max_state.reset_for_new_day()
            mock_reset.assert_called_once()


class TestDailyMaxStateGetStateDict:
    """Tests for get_state_dict method."""

    def test_get_state_dict_delegates_to_delegator(self, daily_max_state: DailyMaxState) -> None:
        """get_state_dict delegates to StateManager."""
        mock_state_dict = {"max_temp_c": TEST_TEMP_C_25}
        with patch.object(daily_max_state._delegator, "get_state_dict") as mock_get:
            mock_get.return_value = mock_state_dict
            result = daily_max_state.get_state_dict()
            assert result == mock_state_dict
            mock_get.assert_called_once()


class TestDailyMaxStateLoadFromStateDict:
    """Tests for load_from_state_dict method."""

    def test_load_from_state_dict_delegates_to_delegator(self, daily_max_state: DailyMaxState) -> None:
        """load_from_state_dict delegates to StateManager."""
        mock_state_dict = {"max_temp_c": TEST_TEMP_C_30}
        with patch.object(daily_max_state._delegator, "load_from_state_dict") as mock_load:
            daily_max_state.load_from_state_dict(mock_state_dict)
            mock_load.assert_called_once_with(mock_state_dict)


class TestCreateDailyMaxState:
    """Tests for create_daily_max_state factory function."""

    def test_create_daily_max_state_returns_instance(self) -> None:
        """create_daily_max_state returns DailyMaxState instance."""
        with patch("common.daily_max_state.DailyMaxStateFactory.create_metar_config") as mock_config:
            mock_config.return_value = {"precision": TEST_PRECISION_0_1}
            result = create_daily_max_state()
            assert isinstance(result, DailyMaxState)


class TestModuleLazyLoading:
    """Tests for module-level lazy loading."""

    def test_getattr_loads_cli_temp_f_from_src_weather(self) -> None:
        """__getattr__ loads cli_temp_f from src.weather.temperature_converter."""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.cli_temp_f = lambda x: int(x * 9 / 5 + 32)
            mock_import.return_value = mock_module

            from common import daily_max_state

            result = daily_max_state.cli_temp_f
            assert callable(result)

    def test_getattr_loads_cli_temp_f_from_weather_fallback(self) -> None:
        """__getattr__ loads cli_temp_f from weather.temperature_converter as fallback."""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.cli_temp_f = lambda x: int(x * 9 / 5 + 32)

            def side_effect(module_path):
                if module_path == "src.weather.temperature_converter":
                    raise ImportError("Module not found")
                return mock_module

            mock_import.side_effect = side_effect

            from common import daily_max_state

            result = daily_max_state.cli_temp_f
            assert callable(result)

    def test_getattr_uses_builtin_cli_temp_f_when_no_weather_module(self) -> None:
        """__getattr__ uses builtin cli_temp_f when weather module not available."""
        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("Module not found")

            from common import daily_max_state

            result = daily_max_state.cli_temp_f
            assert callable(result)
            assert result(0) == 32
            assert result(100) == 212

    def test_getattr_raises_for_unknown_module_attribute(self) -> None:
        """__getattr__ raises AttributeError for unknown attribute."""
        from common import daily_max_state

        with pytest.raises(AttributeError, match="has no attribute 'unknown_function'"):
            _ = daily_max_state.unknown_function


class TestLoadCliTempF:
    """Tests for _load_cli_temp_f function."""

    def test_load_cli_temp_f_tries_src_weather_first(self) -> None:
        """_load_cli_temp_f tries src.weather.temperature_converter first."""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.cli_temp_f = lambda x: int(x * 9 / 5 + 32)
            mock_import.return_value = mock_module

            from common.daily_max_state import _load_cli_temp_f

            result = _load_cli_temp_f()
            assert callable(result)
            mock_import.assert_called_once_with("src.weather.temperature_converter")

    def test_load_cli_temp_f_tries_weather_on_import_error(self) -> None:
        """_load_cli_temp_f tries weather.temperature_converter on ImportError."""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.cli_temp_f = lambda x: int(x * 9 / 5 + 32)

            def side_effect(module_path):
                if module_path == "src.weather.temperature_converter":
                    raise ImportError("Module not found")
                return mock_module

            mock_import.side_effect = side_effect

            from common.daily_max_state import _load_cli_temp_f

            result = _load_cli_temp_f()
            assert callable(result)
            assert mock_import.call_count == 2

    def test_load_cli_temp_f_tries_weather_on_module_not_found_error(self) -> None:
        """_load_cli_temp_f tries weather.temperature_converter on ModuleNotFoundError."""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.cli_temp_f = lambda x: int(x * 9 / 5 + 32)

            def side_effect(module_path):
                if module_path == "src.weather.temperature_converter":
                    raise ModuleNotFoundError("Module not found")
                return mock_module

            mock_import.side_effect = side_effect

            from common.daily_max_state import _load_cli_temp_f

            result = _load_cli_temp_f()
            assert callable(result)

    def test_load_cli_temp_f_tries_weather_on_attribute_error(self) -> None:
        """_load_cli_temp_f tries weather.temperature_converter on AttributeError."""
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.cli_temp_f = lambda x: int(x * 9 / 5 + 32)

            def side_effect(module_path):
                if module_path == "src.weather.temperature_converter":
                    raise AttributeError("Attribute not found")
                return mock_module

            mock_import.side_effect = side_effect

            from common.daily_max_state import _load_cli_temp_f

            result = _load_cli_temp_f()
            assert callable(result)

    def test_load_cli_temp_f_returns_fallback_function(self) -> None:
        """_load_cli_temp_f returns fallback function when all imports fail."""
        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("Module not found")

            from common.daily_max_state import _load_cli_temp_f

            result = _load_cli_temp_f()
            assert callable(result)
            assert result(0) == 32
            assert result(100) == 212
            assert result(TEST_TEMP_C_25) == TEST_TEMP_F_77
