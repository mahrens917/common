"""Tests for service config builder module."""

from unittest.mock import patch

import pytest

from common.connectionconfig_helpers.service_config_builder import (
    build_cfb_config,
    build_websocket_config,
    get_service_specific_config,
)

# Test constants
TEST_CONNECTION_TIMEOUT = 30
TEST_REQUEST_TIMEOUT = 15
TEST_SUBSCRIPTION_TIMEOUT = 20
TEST_RECONNECTION_INITIAL_DELAY = 2
TEST_RECONNECTION_MAX_DELAY = 300
TEST_RECONNECTION_BACKOFF_MULTIPLIER = 2.0
TEST_MAX_CONSECUTIVE_FAILURES = 10
TEST_HEARTBEAT_INTERVAL = 60
TEST_PING_INTERVAL = 25
TEST_PING_TIMEOUT = 5
TEST_CLOSE_TIMEOUT = 5

TEST_CFB_CONNECTION_TIMEOUT = 25
TEST_CFB_REQUEST_TIMEOUT = 15
TEST_CFB_RECONNECTION_INITIAL_DELAY = 5

TEST_WEATHER_CONNECTION_TIMEOUT = 35
TEST_WEATHER_REQUEST_TIMEOUT = 18
TEST_WEATHER_RECONNECTION_INITIAL_DELAY = 4
TEST_WEATHER_RECONNECTION_MAX_DELAY = 400
TEST_WEATHER_RECONNECTION_BACKOFF_MULTIPLIER = 2.5
TEST_WEATHER_MAX_CONSECUTIVE_FAILURES = 12
TEST_WEATHER_HEALTH_CHECK_INTERVAL = 70
TEST_WEATHER_SUBSCRIPTION_TIMEOUT = 150

TEST_SERVICE_NAME_WEATHER = "weather"
TEST_SERVICE_NAME_CFB = "cfb"
TEST_SERVICE_NAME_KALSHI = "kalshi"
TEST_SERVICE_NAME_DERIBIT = "deribit"
TEST_SERVICE_NAME_POLY = "poly"
TEST_SERVICE_NAME_UNKNOWN = "unknown_service"


def _make_flat_ws_config() -> dict:
    """Create a flat websocket config for testing."""
    return {
        "connection": {
            "timeout_seconds": TEST_CONNECTION_TIMEOUT,
            "request_timeout_seconds": TEST_REQUEST_TIMEOUT,
            "reconnection_initial_delay_seconds": TEST_RECONNECTION_INITIAL_DELAY,
            "reconnection_max_delay_seconds": TEST_RECONNECTION_MAX_DELAY,
            "reconnection_backoff_multiplier": TEST_RECONNECTION_BACKOFF_MULTIPLIER,
            "max_consecutive_failures": TEST_MAX_CONSECUTIVE_FAILURES,
            "heartbeat_interval_seconds": TEST_HEARTBEAT_INTERVAL,
            "ping_interval_seconds": TEST_PING_INTERVAL,
            "ping_timeout_seconds": TEST_PING_TIMEOUT,
            "close_timeout_seconds": TEST_CLOSE_TIMEOUT,
        },
        "subscription": {
            "timeout_seconds": TEST_SUBSCRIPTION_TIMEOUT,
        },
    }


class TestBuildWebsocketConfig:
    """Tests for build_websocket_config function."""

    def test_returns_config_with_all_fields(self) -> None:
        """Returns config with all required fields."""
        mock_ws_config = _make_flat_ws_config()

        result = build_websocket_config(mock_ws_config)

        assert result["connection_timeout_seconds"] == TEST_CONNECTION_TIMEOUT
        assert result["request_timeout_seconds"] == TEST_REQUEST_TIMEOUT
        assert result["subscription_timeout_seconds"] == TEST_SUBSCRIPTION_TIMEOUT
        assert result["reconnection_initial_delay_seconds"] == TEST_RECONNECTION_INITIAL_DELAY
        assert result["reconnection_max_delay_seconds"] == TEST_RECONNECTION_MAX_DELAY
        assert result["reconnection_backoff_multiplier"] == TEST_RECONNECTION_BACKOFF_MULTIPLIER
        assert result["max_consecutive_failures"] == TEST_MAX_CONSECUTIVE_FAILURES
        assert result["health_check_interval_seconds"] == TEST_HEARTBEAT_INTERVAL
        assert result["ping_interval_seconds"] == TEST_PING_INTERVAL
        assert result["ping_timeout_seconds"] == TEST_PING_TIMEOUT
        assert result["close_timeout_seconds"] == TEST_CLOSE_TIMEOUT

    def test_raises_key_error_when_missing_connection_key(self) -> None:
        """Raises KeyError when connection key is missing."""
        mock_ws_config = {"subscription": {"timeout_seconds": TEST_SUBSCRIPTION_TIMEOUT}}

        with pytest.raises(KeyError):
            build_websocket_config(mock_ws_config)

    def test_raises_key_error_when_missing_subscription_key(self) -> None:
        """Raises KeyError when subscription key is missing."""
        mock_ws_config = {"connection": {}}

        with pytest.raises(KeyError):
            build_websocket_config(mock_ws_config)


class TestBuildCfbConfig:
    """Tests for build_cfb_config function."""

    def test_returns_cfb_config_with_all_fields(self) -> None:
        """Returns CFB config with all required fields."""
        with patch("common.connectionconfig_helpers.service_config_builder.env_int") as mock_env_int:
            mock_env_int.side_effect = [
                TEST_CFB_CONNECTION_TIMEOUT,
                TEST_CFB_REQUEST_TIMEOUT,
                TEST_CFB_RECONNECTION_INITIAL_DELAY,
            ]
            with patch("common.connectionconfig_helpers.service_config_builder.resolve_cfb_setting") as mock_resolve:
                mock_resolve.side_effect = [
                    TEST_CFB_CONNECTION_TIMEOUT,
                    TEST_CFB_REQUEST_TIMEOUT,
                    TEST_CFB_RECONNECTION_INITIAL_DELAY,
                ]

                result = build_cfb_config()

        assert result["connection_timeout_seconds"] == TEST_CFB_CONNECTION_TIMEOUT
        assert result["request_timeout_seconds"] == TEST_CFB_REQUEST_TIMEOUT
        assert result["reconnection_initial_delay_seconds"] == TEST_CFB_RECONNECTION_INITIAL_DELAY


class TestGetServiceSpecificConfig:
    """Tests for get_service_specific_config function."""

    def test_returns_weather_config_when_service_name_is_weather(self) -> None:
        """Returns weather config when service name is weather."""
        mock_weather_config = {
            "connection_timeout_seconds": TEST_WEATHER_CONNECTION_TIMEOUT,
            "request_timeout_seconds": TEST_WEATHER_REQUEST_TIMEOUT,
            "reconnection_initial_delay_seconds": TEST_WEATHER_RECONNECTION_INITIAL_DELAY,
            "reconnection_max_delay_seconds": TEST_WEATHER_RECONNECTION_MAX_DELAY,
            "reconnection_backoff_multiplier": TEST_WEATHER_RECONNECTION_BACKOFF_MULTIPLIER,
            "max_consecutive_failures": TEST_WEATHER_MAX_CONSECUTIVE_FAILURES,
            "health_check_interval_seconds": TEST_WEATHER_HEALTH_CHECK_INTERVAL,
            "subscription_timeout_seconds": TEST_WEATHER_SUBSCRIPTION_TIMEOUT,
        }
        with patch(
            "common.connectionconfig_helpers.config_loader.load_weather_config",
            return_value=mock_weather_config,
        ):
            result = get_service_specific_config(TEST_SERVICE_NAME_WEATHER)

        assert result == mock_weather_config

    def test_returns_cfb_config_when_service_name_is_cfb(self) -> None:
        """Returns CFB config when service name is cfb."""
        mock_cfb_config = {
            "connection_timeout_seconds": TEST_CFB_CONNECTION_TIMEOUT,
            "request_timeout_seconds": TEST_CFB_REQUEST_TIMEOUT,
            "reconnection_initial_delay_seconds": TEST_CFB_RECONNECTION_INITIAL_DELAY,
        }
        with patch(
            "common.connectionconfig_helpers.service_config_builder.build_cfb_config",
            return_value=mock_cfb_config,
        ):
            result = get_service_specific_config(TEST_SERVICE_NAME_CFB)

        assert result == mock_cfb_config

    def test_returns_websocket_config_when_service_name_is_kalshi(self) -> None:
        """Returns websocket config when service name is kalshi."""
        mock_ws_config = _make_flat_ws_config()
        with patch(
            "common.connectionconfig_helpers.service_config_builder.load_websocket_config",
            return_value=mock_ws_config,
        ):
            result = get_service_specific_config(TEST_SERVICE_NAME_KALSHI)

        assert result["connection_timeout_seconds"] == TEST_CONNECTION_TIMEOUT
        assert result["request_timeout_seconds"] == TEST_REQUEST_TIMEOUT
        assert result["subscription_timeout_seconds"] == TEST_SUBSCRIPTION_TIMEOUT

    def test_returns_websocket_config_when_service_name_is_deribit(self) -> None:
        """Returns websocket config when service name is deribit."""
        mock_ws_config = _make_flat_ws_config()
        with patch(
            "common.connectionconfig_helpers.service_config_builder.load_websocket_config",
            return_value=mock_ws_config,
        ):
            result = get_service_specific_config(TEST_SERVICE_NAME_DERIBIT)

        assert result["connection_timeout_seconds"] == TEST_CONNECTION_TIMEOUT
        assert result["request_timeout_seconds"] == TEST_REQUEST_TIMEOUT

    def test_returns_websocket_config_when_service_name_is_poly(self) -> None:
        """Returns websocket config when service name is poly."""
        mock_ws_config = _make_flat_ws_config()
        with patch(
            "common.connectionconfig_helpers.service_config_builder.load_websocket_config",
            return_value=mock_ws_config,
        ):
            result = get_service_specific_config(TEST_SERVICE_NAME_POLY)

        assert result["ping_interval_seconds"] == TEST_PING_INTERVAL
        assert result["ping_timeout_seconds"] == TEST_PING_TIMEOUT

    def test_returns_empty_dict_for_unknown_service_name(self) -> None:
        """Returns empty dict for unknown service name."""
        with patch(
            "common.connectionconfig_helpers.service_config_builder.load_websocket_config",
            return_value={},
        ):
            result = get_service_specific_config(TEST_SERVICE_NAME_UNKNOWN)

        assert result == {}
