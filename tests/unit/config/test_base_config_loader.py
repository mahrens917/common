"""
Tests for src/common/config_loader.py

Tests configuration loading utilities and BaseConfigLoader class.
"""

import json
import tempfile
from datetime import date
from pathlib import Path

import pytest

from common.config_loader import (
    BaseConfigLoader,
    get_historical_start_date,
    get_reporting_timezone,
    load_config,
    load_pnl_config,
    load_weather_trading_config,
)
from common.exceptions import ConfigurationError


class TestBaseConfigLoader:
    """Tests for BaseConfigLoader class."""

    def test_init_sets_config_dir(self, tmp_path):
        """__init__ sets the config directory."""
        loader = BaseConfigLoader(tmp_path)
        assert loader.config_dir == tmp_path
        assert loader._cached_config is None

    def test_load_json_file_loads_valid_config(self, tmp_path):
        """load_json_file loads valid JSON configuration."""
        config_file = tmp_path / "test.json"
        test_config = {"key": "value", "number": 42}
        config_file.write_text(json.dumps(test_config))

        loader = BaseConfigLoader(tmp_path)
        result = loader.load_json_file("test.json")

        assert result == test_config

    def test_load_json_file_raises_on_missing_file(self, tmp_path):
        """load_json_file raises FileNotFoundError when file doesn't exist."""
        loader = BaseConfigLoader(tmp_path)

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            loader.load_json_file("nonexistent.json")

    def test_load_json_file_raises_on_invalid_json(self, tmp_path):
        """load_json_file raises ConfigurationError on invalid JSON."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{ invalid json }")

        loader = BaseConfigLoader(tmp_path)

        with pytest.raises(ConfigurationError, match="Invalid JSON"):
            loader.load_json_file("invalid.json")

    def test_get_section_returns_section(self):
        """get_section returns the requested section."""
        loader = BaseConfigLoader(Path("."))
        config = {"section1": {"key": "value"}, "section2": {"other": "data"}}

        result = loader.get_section(config, "section1")

        assert result == {"key": "value"}

    def test_get_section_raises_on_missing_section(self):
        """get_section raises ConfigurationError when section not found."""
        loader = BaseConfigLoader(Path("."))
        config = {"section1": {}}

        with pytest.raises(ConfigurationError, match="section not found: section2"):
            loader.get_section(config, "section2")

    def test_get_section_raises_on_non_dict_section(self):
        """get_section raises ConfigurationError when section is not a dict."""
        loader = BaseConfigLoader(Path("."))
        config = {"section1": "not_a_dict"}

        with pytest.raises(ConfigurationError, match="must be a dict"):
            loader.get_section(config, "section1")

    def test_get_parameter_returns_parameter_value(self):
        """get_parameter returns the parameter value from section."""
        loader = BaseConfigLoader(Path("."))
        config = {"section1": {"param1": "value1", "param2": 123}}

        result = loader.get_parameter(config, "section1", "param1")

        assert result == "value1"

    def test_get_parameter_raises_on_missing_parameter(self):
        """get_parameter raises ConfigurationError when parameter not found."""
        loader = BaseConfigLoader(Path("."))
        config = {"section1": {"param1": "value1"}}

        with pytest.raises(ConfigurationError, match="Parameter 'param2' not found"):
            loader.get_parameter(config, "section1", "param2")

    def test_get_parameter_raises_on_missing_section(self):
        """get_parameter raises ConfigurationError when section not found."""
        loader = BaseConfigLoader(Path("."))
        config = {"section1": {}}

        with pytest.raises(ConfigurationError, match="section not found"):
            loader.get_parameter(config, "section2", "param1")


class TestLoadConfig:
    """Tests for load_config() function."""

    def test_load_config_delegates_to_base_loader(self, monkeypatch, tmp_path):
        """load_config delegates to BaseConfigLoader."""
        config_file = tmp_path / "test.json"
        test_config = {"test": "data"}
        config_file.write_text(json.dumps(test_config))

        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        result = load_config("test.json")

        assert result == test_config

    def test_load_config_raises_on_missing_file(self, monkeypatch, tmp_path):
        """load_config raises FileNotFoundError when file missing."""
        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        with pytest.raises(FileNotFoundError):
            load_config("missing.json")


class TestLoadPnlConfig:
    """Tests for load_pnl_config() function."""

    def test_load_pnl_config_loads_valid_config(self, monkeypatch, tmp_path):
        """load_pnl_config loads valid PnL configuration."""
        config_file = tmp_path / "pnl_config.json"
        test_config = {
            "trade_collection": {"historical_start_date": "2024-01-01"},
            "reporting": {"timezone": "America/New_York"},
        }
        config_file.write_text(json.dumps(test_config))

        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        result = load_pnl_config()

        assert result == test_config

    def test_load_pnl_config_raises_on_missing_file(self, monkeypatch, tmp_path):
        """load_pnl_config raises FileNotFoundError when file missing."""
        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        with pytest.raises(FileNotFoundError, match="PnL config file not found"):
            load_pnl_config()

    def test_load_pnl_config_raises_on_invalid_json(self, monkeypatch, tmp_path):
        """load_pnl_config raises RuntimeError on invalid JSON."""
        config_file = tmp_path / "pnl_config.json"
        config_file.write_text("{ invalid json }")

        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        with pytest.raises(RuntimeError, match="Invalid JSON"):
            load_pnl_config()

    def test_load_pnl_config_raises_on_missing_trade_collection_section(
        self, monkeypatch, tmp_path
    ):
        """load_pnl_config raises RuntimeError when trade_collection section missing."""
        config_file = tmp_path / "pnl_config.json"
        config_file.write_text(json.dumps({}))

        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        with pytest.raises(RuntimeError, match="Missing 'trade_collection' section"):
            load_pnl_config()

    def test_load_pnl_config_raises_on_missing_historical_start_date(self, monkeypatch, tmp_path):
        """load_pnl_config raises RuntimeError when historical_start_date missing."""
        config_file = tmp_path / "pnl_config.json"
        config_file.write_text(json.dumps({"trade_collection": {}}))

        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        with pytest.raises(RuntimeError, match="Missing 'historical_start_date'"):
            load_pnl_config()


class TestGetHistoricalStartDate:
    """Tests for get_historical_start_date() function."""

    def test_get_historical_start_date_returns_date(self, monkeypatch, tmp_path):
        """get_historical_start_date returns parsed date from config."""
        config_file = tmp_path / "pnl_config.json"
        test_config = {
            "trade_collection": {"historical_start_date": "2024-01-15"},
        }
        config_file.write_text(json.dumps(test_config))

        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        result = get_historical_start_date()

        assert result == date(2024, 1, 15)

    def test_get_historical_start_date_raises_on_invalid_date_format(self, monkeypatch, tmp_path):
        """get_historical_start_date raises RuntimeError on invalid date format."""
        config_file = tmp_path / "pnl_config.json"
        test_config = {
            "trade_collection": {"historical_start_date": "not-a-date"},
        }
        config_file.write_text(json.dumps(test_config))

        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        with pytest.raises(RuntimeError, match="Invalid date format"):
            get_historical_start_date()

    def test_get_historical_start_date_raises_on_config_error(self, monkeypatch, tmp_path):
        """get_historical_start_date raises RuntimeError on config loading error."""
        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        with pytest.raises(RuntimeError, match="Failed to load historical start date"):
            get_historical_start_date()


class TestGetReportingTimezone:
    """Tests for get_reporting_timezone() function."""

    def test_get_reporting_timezone_returns_timezone(self, monkeypatch, tmp_path):
        """get_reporting_timezone returns timezone string from config."""
        config_file = tmp_path / "pnl_config.json"
        test_config = {
            "trade_collection": {"historical_start_date": "2024-01-01"},
            "reporting": {"timezone": "America/New_York"},
        }
        config_file.write_text(json.dumps(test_config))

        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        result = get_reporting_timezone()

        assert result == "America/New_York"

    def test_get_reporting_timezone_strips_whitespace(self, monkeypatch, tmp_path):
        """get_reporting_timezone strips whitespace from timezone value."""
        config_file = tmp_path / "pnl_config.json"
        test_config = {
            "trade_collection": {"historical_start_date": "2024-01-01"},
            "reporting": {"timezone": "  UTC  "},
        }
        config_file.write_text(json.dumps(test_config))

        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        result = get_reporting_timezone()

        assert result == "UTC"

    def test_get_reporting_timezone_raises_on_missing_reporting_section(
        self, monkeypatch, tmp_path
    ):
        """get_reporting_timezone raises RuntimeError when reporting section missing."""
        config_file = tmp_path / "pnl_config.json"
        test_config = {
            "trade_collection": {"historical_start_date": "2024-01-01"},
        }
        config_file.write_text(json.dumps(test_config))

        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        with pytest.raises(TypeError, match="missing 'reporting' section"):
            get_reporting_timezone()

    def test_get_reporting_timezone_raises_on_non_dict_reporting(self, monkeypatch, tmp_path):
        """get_reporting_timezone raises RuntimeError when reporting is not a dict."""
        config_file = tmp_path / "pnl_config.json"
        test_config = {
            "trade_collection": {"historical_start_date": "2024-01-01"},
            "reporting": "not_a_dict",
        }
        config_file.write_text(json.dumps(test_config))

        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        with pytest.raises(TypeError, match="missing 'reporting' section"):
            get_reporting_timezone()

    def test_get_reporting_timezone_raises_on_missing_timezone_value(self, monkeypatch, tmp_path):
        """get_reporting_timezone raises RuntimeError when timezone value missing."""
        config_file = tmp_path / "pnl_config.json"
        test_config = {
            "trade_collection": {"historical_start_date": "2024-01-01"},
            "reporting": {},
        }
        config_file.write_text(json.dumps(test_config))

        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        with pytest.raises(TypeError, match="non-empty reporting timezone"):
            get_reporting_timezone()

    def test_get_reporting_timezone_raises_on_empty_timezone_value(self, monkeypatch, tmp_path):
        """get_reporting_timezone raises RuntimeError on empty timezone value."""
        config_file = tmp_path / "pnl_config.json"
        test_config = {
            "trade_collection": {"historical_start_date": "2024-01-01"},
            "reporting": {"timezone": "   "},
        }
        config_file.write_text(json.dumps(test_config))

        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        with pytest.raises(RuntimeError, match="non-empty reporting timezone"):
            get_reporting_timezone()


class TestLoadWeatherTradingConfig:
    """Tests for load_weather_trading_config() function."""

    def test_load_weather_trading_config_loads_valid_config(self, monkeypatch, tmp_path):
        """load_weather_trading_config loads valid configuration."""
        config_file = tmp_path / "weather_trading_config.json"
        test_config = {"trading_enabled": True, "max_position_size": 100}
        config_file.write_text(json.dumps(test_config))

        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        result = load_weather_trading_config()

        assert result == test_config

    def test_load_weather_trading_config_raises_on_missing_file(self, monkeypatch, tmp_path):
        """load_weather_trading_config raises FileNotFoundError when file missing."""
        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        with pytest.raises(FileNotFoundError, match="Weather trading config file not found"):
            load_weather_trading_config()

    def test_load_weather_trading_config_raises_on_invalid_json(self, monkeypatch, tmp_path):
        """load_weather_trading_config raises RuntimeError on invalid JSON."""
        config_file = tmp_path / "weather_trading_config.json"
        config_file.write_text("{ invalid json }")

        monkeypatch.setattr("common.config_loader._CONFIG_DIR", tmp_path)

        with pytest.raises(RuntimeError, match="Invalid JSON"):
            load_weather_trading_config()
