"""Tests for service config builder module."""

from unittest.mock import patch

import pytest

from common.connectionconfig_helpers.service_config_builder import (
    build_cfb_config,
    build_deribit_config,
    build_kalshi_config,
    get_service_specific_config,
)

# Test constants
TEST_KALSHI_CONNECTION_TIMEOUT = 30
TEST_KALSHI_REQUEST_TIMEOUT = 15
TEST_KALSHI_SUBSCRIPTION_TIMEOUT = 20
TEST_KALSHI_RECONNECTION_INITIAL_DELAY = 2
TEST_KALSHI_RECONNECTION_MAX_DELAY = 300
TEST_KALSHI_RECONNECTION_BACKOFF_MULTIPLIER = 2.0
TEST_KALSHI_MAX_CONSECUTIVE_FAILURES = 10
TEST_KALSHI_HEARTBEAT_INTERVAL = 60
TEST_KALSHI_PING_INTERVAL = 25
TEST_KALSHI_PING_TIMEOUT = 5

TEST_DERIBIT_CONNECTION_TIMEOUT = 25
TEST_DERIBIT_REQUEST_TIMEOUT = 10
TEST_DERIBIT_RECONNECTION_INITIAL_DELAY = 3
TEST_DERIBIT_RECONNECTION_MAX_DELAY = 200
TEST_DERIBIT_RECONNECTION_BACKOFF_MULTIPLIER = 1.5
TEST_DERIBIT_MAX_CONSECUTIVE_FAILURES = 8
TEST_DERIBIT_HEARTBEAT_INTERVAL = 50
TEST_DERIBIT_PING_INTERVAL = 20
TEST_DERIBIT_PING_TIMEOUT = 10

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
TEST_SERVICE_NAME_UNKNOWN = "unknown_service"


class TestBuildKalshiConfig:
    """Tests for build_kalshi_config function."""

    def test_returns_kalshi_config_with_all_fields(self) -> None:
        """Returns Kalshi config with all required fields."""
        mock_ws_config = {
            "kalshi": {
                "connection": {
                    "timeout_seconds": TEST_KALSHI_CONNECTION_TIMEOUT,
                    "request_timeout_seconds": TEST_KALSHI_REQUEST_TIMEOUT,
                    "reconnection_initial_delay_seconds": TEST_KALSHI_RECONNECTION_INITIAL_DELAY,
                    "reconnection_max_delay_seconds": TEST_KALSHI_RECONNECTION_MAX_DELAY,
                    "reconnection_backoff_multiplier": TEST_KALSHI_RECONNECTION_BACKOFF_MULTIPLIER,
                    "max_consecutive_failures": TEST_KALSHI_MAX_CONSECUTIVE_FAILURES,
                    "heartbeat_interval_seconds": TEST_KALSHI_HEARTBEAT_INTERVAL,
                    "ping_interval_seconds": TEST_KALSHI_PING_INTERVAL,
                    "ping_timeout_seconds": TEST_KALSHI_PING_TIMEOUT,
                },
                "subscription": {
                    "timeout_seconds": TEST_KALSHI_SUBSCRIPTION_TIMEOUT,
                },
            }
        }

        result = build_kalshi_config(mock_ws_config)

        assert result["connection_timeout_seconds"] == TEST_KALSHI_CONNECTION_TIMEOUT
        assert result["request_timeout_seconds"] == TEST_KALSHI_REQUEST_TIMEOUT
        assert result["subscription_timeout_seconds"] == TEST_KALSHI_SUBSCRIPTION_TIMEOUT
        assert result["reconnection_initial_delay_seconds"] == TEST_KALSHI_RECONNECTION_INITIAL_DELAY
        assert result["reconnection_max_delay_seconds"] == TEST_KALSHI_RECONNECTION_MAX_DELAY
        assert result["reconnection_backoff_multiplier"] == TEST_KALSHI_RECONNECTION_BACKOFF_MULTIPLIER
        assert result["max_consecutive_failures"] == TEST_KALSHI_MAX_CONSECUTIVE_FAILURES
        assert result["health_check_interval_seconds"] == TEST_KALSHI_HEARTBEAT_INTERVAL
        assert result["ping_interval_seconds"] == TEST_KALSHI_PING_INTERVAL
        assert result["ping_timeout_seconds"] == TEST_KALSHI_PING_TIMEOUT

    def test_raises_key_error_when_missing_kalshi_key(self) -> None:
        """Raises KeyError when kalshi key is missing."""
        mock_ws_config = {"other_service": {}}

        with pytest.raises(KeyError):
            build_kalshi_config(mock_ws_config)

    def test_raises_key_error_when_missing_connection_key(self) -> None:
        """Raises KeyError when connection key is missing."""
        mock_ws_config = {"kalshi": {"subscription": {}}}

        with pytest.raises(KeyError):
            build_kalshi_config(mock_ws_config)

    def test_raises_key_error_when_missing_subscription_key(self) -> None:
        """Raises KeyError when subscription key is missing."""
        mock_ws_config = {"kalshi": {"connection": {}}}

        with pytest.raises(KeyError):
            build_kalshi_config(mock_ws_config)


class TestBuildDeribitConfig:
    """Tests for build_deribit_config function."""

    def test_returns_deribit_config_with_all_fields(self) -> None:
        """Returns Deribit config with all required fields."""
        mock_ws_config = {
            "deribit": {
                "connection": {
                    "timeout_seconds": TEST_DERIBIT_CONNECTION_TIMEOUT,
                    "request_timeout_seconds": TEST_DERIBIT_REQUEST_TIMEOUT,
                    "reconnection_initial_delay_seconds": TEST_DERIBIT_RECONNECTION_INITIAL_DELAY,
                    "reconnection_max_delay_seconds": TEST_DERIBIT_RECONNECTION_MAX_DELAY,
                    "reconnection_backoff_multiplier": TEST_DERIBIT_RECONNECTION_BACKOFF_MULTIPLIER,
                    "max_consecutive_failures": TEST_DERIBIT_MAX_CONSECUTIVE_FAILURES,
                    "heartbeat_interval_seconds": TEST_DERIBIT_HEARTBEAT_INTERVAL,
                    "ping_interval_seconds": TEST_DERIBIT_PING_INTERVAL,
                    "ping_timeout_seconds": TEST_DERIBIT_PING_TIMEOUT,
                }
            }
        }

        result = build_deribit_config(mock_ws_config)

        assert result["connection_timeout_seconds"] == TEST_DERIBIT_CONNECTION_TIMEOUT
        assert result["request_timeout_seconds"] == TEST_DERIBIT_REQUEST_TIMEOUT
        assert result["reconnection_initial_delay_seconds"] == TEST_DERIBIT_RECONNECTION_INITIAL_DELAY
        assert result["reconnection_max_delay_seconds"] == TEST_DERIBIT_RECONNECTION_MAX_DELAY
        assert result["reconnection_backoff_multiplier"] == TEST_DERIBIT_RECONNECTION_BACKOFF_MULTIPLIER
        assert result["max_consecutive_failures"] == TEST_DERIBIT_MAX_CONSECUTIVE_FAILURES
        assert result["health_check_interval_seconds"] == TEST_DERIBIT_HEARTBEAT_INTERVAL
        assert result["ping_interval_seconds"] == TEST_DERIBIT_PING_INTERVAL
        assert result["ping_timeout_seconds"] == TEST_DERIBIT_PING_TIMEOUT

    def test_raises_key_error_when_missing_deribit_key(self) -> None:
        """Raises KeyError when deribit key is missing."""
        mock_ws_config = {"other_service": {}}

        with pytest.raises(KeyError):
            build_deribit_config(mock_ws_config)

    def test_raises_key_error_when_missing_connection_key(self) -> None:
        """Raises KeyError when connection key is missing."""
        mock_ws_config = {"deribit": {}}

        with pytest.raises(KeyError):
            build_deribit_config(mock_ws_config)


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

    def test_returns_kalshi_config_when_service_name_is_kalshi(self) -> None:
        """Returns Kalshi config when service name is kalshi."""
        mock_ws_config = {
            "kalshi": {
                "connection": {
                    "timeout_seconds": TEST_KALSHI_CONNECTION_TIMEOUT,
                    "request_timeout_seconds": TEST_KALSHI_REQUEST_TIMEOUT,
                    "reconnection_initial_delay_seconds": TEST_KALSHI_RECONNECTION_INITIAL_DELAY,
                    "reconnection_max_delay_seconds": TEST_KALSHI_RECONNECTION_MAX_DELAY,
                    "reconnection_backoff_multiplier": TEST_KALSHI_RECONNECTION_BACKOFF_MULTIPLIER,
                    "max_consecutive_failures": TEST_KALSHI_MAX_CONSECUTIVE_FAILURES,
                    "heartbeat_interval_seconds": TEST_KALSHI_HEARTBEAT_INTERVAL,
                    "ping_interval_seconds": TEST_KALSHI_PING_INTERVAL,
                    "ping_timeout_seconds": TEST_KALSHI_PING_TIMEOUT,
                },
                "subscription": {
                    "timeout_seconds": TEST_KALSHI_SUBSCRIPTION_TIMEOUT,
                },
            }
        }
        with patch(
            "common.connectionconfig_helpers.service_config_builder.load_websocket_config",
            return_value=mock_ws_config,
        ):
            result = get_service_specific_config(TEST_SERVICE_NAME_KALSHI)

        assert result["connection_timeout_seconds"] == TEST_KALSHI_CONNECTION_TIMEOUT
        assert result["request_timeout_seconds"] == TEST_KALSHI_REQUEST_TIMEOUT
        assert result["subscription_timeout_seconds"] == TEST_KALSHI_SUBSCRIPTION_TIMEOUT

    def test_returns_deribit_config_when_service_name_is_deribit(self) -> None:
        """Returns Deribit config when service name is deribit."""
        mock_ws_config = {
            "deribit": {
                "connection": {
                    "timeout_seconds": TEST_DERIBIT_CONNECTION_TIMEOUT,
                    "request_timeout_seconds": TEST_DERIBIT_REQUEST_TIMEOUT,
                    "reconnection_initial_delay_seconds": TEST_DERIBIT_RECONNECTION_INITIAL_DELAY,
                    "reconnection_max_delay_seconds": TEST_DERIBIT_RECONNECTION_MAX_DELAY,
                    "reconnection_backoff_multiplier": TEST_DERIBIT_RECONNECTION_BACKOFF_MULTIPLIER,
                    "max_consecutive_failures": TEST_DERIBIT_MAX_CONSECUTIVE_FAILURES,
                    "heartbeat_interval_seconds": TEST_DERIBIT_HEARTBEAT_INTERVAL,
                    "ping_interval_seconds": TEST_DERIBIT_PING_INTERVAL,
                    "ping_timeout_seconds": TEST_DERIBIT_PING_TIMEOUT,
                }
            }
        }
        with patch(
            "common.connectionconfig_helpers.service_config_builder.load_websocket_config",
            return_value=mock_ws_config,
        ):
            result = get_service_specific_config(TEST_SERVICE_NAME_DERIBIT)

        assert result["connection_timeout_seconds"] == TEST_DERIBIT_CONNECTION_TIMEOUT
        assert result["request_timeout_seconds"] == TEST_DERIBIT_REQUEST_TIMEOUT

    def test_returns_empty_dict_for_unknown_service_name(self) -> None:
        """Returns empty dict for unknown service name."""
        with patch(
            "common.connectionconfig_helpers.service_config_builder.load_websocket_config",
            return_value={},
        ):
            result = get_service_specific_config(TEST_SERVICE_NAME_UNKNOWN)

        assert result == {}
