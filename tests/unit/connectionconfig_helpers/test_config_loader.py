"""Tests for config loader module."""

from unittest.mock import patch

import pytest

from src.common.connectionconfig_helpers.config_loader import (
    load_weather_config,
    load_websocket_config,
    require_env_float,
    require_env_int,
    resolve_cfb_setting,
)
from src.common.exceptions import ConfigurationError


class TestRequireEnvInt:
    """Tests for require_env_int function."""

    def test_returns_env_value_when_set(self) -> None:
        """Returns environment value when set."""
        with patch(
            "src.common.connectionconfig_helpers.config_loader.env_int",
            return_value=42,
        ):
            result = require_env_int("CUSTOM_VAR")

        assert result == 42

    def test_recommends_value_for_known_variable(self) -> None:
        """Reports a recommended value when a known variable is missing."""
        with patch(
            "src.common.connectionconfig_helpers.config_loader.env_int",
            return_value=None,
        ):
            with pytest.raises(ConfigurationError, match="recommended"):
                require_env_int("CONNECTION_TIMEOUT_SECONDS")

    def test_raises_for_unknown_variable(self) -> None:
        """Raises ConfigurationError for unknown variable when env not set."""
        with patch(
            "src.common.connectionconfig_helpers.config_loader.env_int",
            return_value=None,
        ):
            with pytest.raises(ConfigurationError, match="must be defined"):
                require_env_int("UNKNOWN_VARIABLE")


class TestRequireEnvFloat:
    """Tests for require_env_float function."""

    def test_returns_env_value_when_set(self) -> None:
        """Returns environment value when set."""
        with patch(
            "src.common.connectionconfig_helpers.config_loader.env_float",
            return_value=3.14,
        ):
            result = require_env_float("CUSTOM_VAR")

        assert result == 3.14

    def test_recommends_value_for_known_variable(self) -> None:
        """Reports a recommended value when a known variable is missing."""
        with patch(
            "src.common.connectionconfig_helpers.config_loader.env_float",
            return_value=None,
        ):
            with pytest.raises(ConfigurationError, match="recommended"):
                require_env_float("RECONNECTION_BACKOFF_MULTIPLIER")

    def test_raises_for_unknown_variable(self) -> None:
        """Raises ConfigurationError for unknown variable when env not set."""
        with patch(
            "src.common.connectionconfig_helpers.config_loader.env_float",
            return_value=None,
        ):
            with pytest.raises(ConfigurationError, match="must be defined"):
                require_env_float("UNKNOWN_VARIABLE")


class TestResolveCfbSetting:
    """Tests for resolve_cfb_setting function."""

    def test_returns_value_when_provided(self) -> None:
        """Returns value when provided."""
        result = resolve_cfb_setting(42, default_value=10)

        assert result == 42

    def test_returns_default_when_none(self) -> None:
        """Returns default when value is None."""
        result = resolve_cfb_setting(None, default_value=10)

        assert result == 10

    def test_returns_zero_when_explicitly_set(self) -> None:
        """Returns zero when explicitly set to zero."""
        result = resolve_cfb_setting(0, default_value=10)

        assert result == 0


class TestLoadWebsocketConfig:
    """Tests for load_websocket_config function."""

    def test_returns_config_when_file_exists(self) -> None:
        """Returns config when file exists."""
        mock_config = {"host": "localhost", "port": 8080}
        with patch(
            "src.common.connectionconfig_helpers.config_loader.load_config",
            return_value=mock_config,
        ):
            result = load_websocket_config()

        assert result == mock_config

    def test_returns_empty_dict_when_file_not_found(self) -> None:
        """Returns empty dict when file not found."""
        with patch(
            "src.common.connectionconfig_helpers.config_loader.load_config",
            side_effect=FileNotFoundError,
        ):
            result = load_websocket_config()

        assert result == {}


class TestLoadWeatherConfig:
    """Tests for load_weather_config function."""

    def test_returns_timeout_values_from_config(self) -> None:
        """Returns timeout values from config."""
        mock_config = {
            "connection_timeout_seconds": 30,
            "request_timeout_seconds": 15,
            "reconnection_initial_delay_seconds": 2,
            "extra_field": "ignored",
        }
        with patch(
            "src.common.connectionconfig_helpers.config_loader.load_config",
            return_value=mock_config,
        ):
            result = load_weather_config()

        assert result["connection_timeout_seconds"] == 30
        assert result["request_timeout_seconds"] == 15
        assert result["reconnection_initial_delay_seconds"] == 2
        assert "extra_field" not in result

    def test_raises_file_not_found_when_missing(self) -> None:
        """Raises FileNotFoundError when config file missing."""
        with patch(
            "src.common.connectionconfig_helpers.config_loader.load_config",
            side_effect=FileNotFoundError,
        ):
            with pytest.raises(FileNotFoundError, match="not found"):
                load_weather_config()

    def test_raises_configuration_error_when_missing_field(self) -> None:
        """Raises ConfigurationError when required field missing."""
        mock_config = {
            "connection_timeout_seconds": 30,
            # Missing request_timeout_seconds and reconnection_initial_delay_seconds
        }
        with patch(
            "src.common.connectionconfig_helpers.config_loader.load_config",
            return_value=mock_config,
        ):
            with pytest.raises(ConfigurationError, match="missing required field"):
                load_weather_config()
