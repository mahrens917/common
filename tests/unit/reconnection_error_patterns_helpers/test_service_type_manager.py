"""Tests for service_type_manager module."""

from __future__ import annotations

import pytest

from common.reconnection_error_patterns_helpers.service_type_manager import (
    DEFAULT_SERVICE_TYPE_MAPPING,
    ServiceType,
    ServiceTypeManager,
)


class TestServiceType:
    """Tests for ServiceType enum."""

    def test_websocket_value(self) -> None:
        """WEBSOCKET has correct value."""
        assert ServiceType.WEBSOCKET.value == "websocket"

    def test_rest_value(self) -> None:
        """REST has correct value."""
        assert ServiceType.REST.value == "rest"

    def test_database_value(self) -> None:
        """DATABASE has correct value."""
        assert ServiceType.DATABASE.value == "database"

    def test_scraper_value(self) -> None:
        """SCRAPER has correct value."""
        assert ServiceType.SCRAPER.value == "scraper"

    def test_unknown_value(self) -> None:
        """UNKNOWN has correct value."""
        assert ServiceType.UNKNOWN.value == "unknown"


class TestDefaultServiceTypeMapping:
    """Tests for DEFAULT_SERVICE_TYPE_MAPPING constant."""

    def test_deribit_is_websocket(self) -> None:
        """deribit service is WEBSOCKET type."""
        assert DEFAULT_SERVICE_TYPE_MAPPING["deribit"] == ServiceType.WEBSOCKET

    def test_kalshi_is_websocket(self) -> None:
        """kalshi service is WEBSOCKET type."""
        assert DEFAULT_SERVICE_TYPE_MAPPING["kalshi"] == ServiceType.WEBSOCKET

    def test_cfb_is_scraper(self) -> None:
        """cfb service is SCRAPER type."""
        assert DEFAULT_SERVICE_TYPE_MAPPING["cfb"] == ServiceType.SCRAPER

    def test_weather_is_rest(self) -> None:
        """weather service is REST type."""
        assert DEFAULT_SERVICE_TYPE_MAPPING["weather"] == ServiceType.REST

    def test_tracker_is_rest(self) -> None:
        """tracker service is REST type."""
        assert DEFAULT_SERVICE_TYPE_MAPPING["tracker"] == ServiceType.REST


class TestServiceTypeManagerInit:
    """Tests for ServiceTypeManager initialization."""

    def test_init_with_default_mapping(self) -> None:
        """Initializes with default mapping when no custom mapping provided."""
        manager = ServiceTypeManager()

        assert "deribit" in manager.service_type_mapping
        assert "kalshi" in manager.service_type_mapping
        assert manager.service_type_mapping["deribit"] == ServiceType.WEBSOCKET

    def test_init_with_custom_mapping(self) -> None:
        """Initializes with custom mapping when provided."""
        custom = {"my_service": ServiceType.DATABASE}

        manager = ServiceTypeManager(custom_mapping=custom)

        assert manager.service_type_mapping == custom
        assert "deribit" not in manager.service_type_mapping

    def test_init_creates_copy_of_default(self) -> None:
        """Creates a copy of default mapping, not a reference."""
        manager = ServiceTypeManager()
        manager.service_type_mapping["new_service"] = ServiceType.WEBSOCKET

        # Original default should not be modified
        assert "new_service" not in DEFAULT_SERVICE_TYPE_MAPPING


class TestServiceTypeManagerGetServiceType:
    """Tests for ServiceTypeManager.get_service_type method."""

    def test_returns_websocket_for_deribit(self) -> None:
        """Returns WEBSOCKET for deribit service."""
        manager = ServiceTypeManager()

        result = manager.get_service_type("deribit")

        assert result == ServiceType.WEBSOCKET

    def test_returns_websocket_for_kalshi(self) -> None:
        """Returns WEBSOCKET for kalshi service."""
        manager = ServiceTypeManager()

        result = manager.get_service_type("kalshi")

        assert result == ServiceType.WEBSOCKET

    def test_returns_scraper_for_cfb(self) -> None:
        """Returns SCRAPER for cfb service."""
        manager = ServiceTypeManager()

        result = manager.get_service_type("cfb")

        assert result == ServiceType.SCRAPER

    def test_returns_rest_for_weather(self) -> None:
        """Returns REST for weather service."""
        manager = ServiceTypeManager()

        result = manager.get_service_type("weather")

        assert result == ServiceType.REST

    def test_returns_unknown_for_unmapped_service(self) -> None:
        """Returns UNKNOWN for unmapped service name."""
        manager = ServiceTypeManager()

        result = manager.get_service_type("nonexistent_service")

        assert result == ServiceType.UNKNOWN

    def test_returns_custom_mapping_value(self) -> None:
        """Returns value from custom mapping."""
        custom = {"custom_db": ServiceType.DATABASE}
        manager = ServiceTypeManager(custom_mapping=custom)

        result = manager.get_service_type("custom_db")

        assert result == ServiceType.DATABASE


class TestServiceTypeManagerAddMapping:
    """Tests for ServiceTypeManager.add_mapping method."""

    def test_adds_new_mapping(self) -> None:
        """Adds new service type mapping."""
        manager = ServiceTypeManager()

        manager.add_mapping("new_service", ServiceType.DATABASE)

        assert manager.service_type_mapping["new_service"] == ServiceType.DATABASE
        assert manager.get_service_type("new_service") == ServiceType.DATABASE

    def test_updates_existing_mapping(self) -> None:
        """Updates existing service type mapping."""
        manager = ServiceTypeManager()
        assert manager.get_service_type("deribit") == ServiceType.WEBSOCKET

        manager.add_mapping("deribit", ServiceType.REST)

        assert manager.service_type_mapping["deribit"] == ServiceType.REST
        assert manager.get_service_type("deribit") == ServiceType.REST


class TestServiceTypeManagerStringToServiceType:
    """Tests for ServiceTypeManager.string_to_service_type method."""

    def test_converts_websocket_string(self) -> None:
        """Converts 'websocket' string to WEBSOCKET enum."""
        manager = ServiceTypeManager()

        result = manager.string_to_service_type("websocket")

        assert result == ServiceType.WEBSOCKET

    def test_converts_rest_string(self) -> None:
        """Converts 'rest' string to REST enum."""
        manager = ServiceTypeManager()

        result = manager.string_to_service_type("rest")

        assert result == ServiceType.REST

    def test_converts_scraper_string(self) -> None:
        """Converts 'scraper' string to SCRAPER enum."""
        manager = ServiceTypeManager()

        result = manager.string_to_service_type("scraper")

        assert result == ServiceType.SCRAPER

    def test_converts_database_string(self) -> None:
        """Converts 'database' string to DATABASE enum."""
        manager = ServiceTypeManager()

        result = manager.string_to_service_type("database")

        assert result == ServiceType.DATABASE

    def test_handles_uppercase_input(self) -> None:
        """Handles uppercase input by converting to lowercase."""
        manager = ServiceTypeManager()

        result = manager.string_to_service_type("WEBSOCKET")

        assert result == ServiceType.WEBSOCKET

    def test_handles_mixed_case_input(self) -> None:
        """Handles mixed case input by converting to lowercase."""
        manager = ServiceTypeManager()

        result = manager.string_to_service_type("WebSocket")

        assert result == ServiceType.WEBSOCKET

    def test_returns_none_for_unknown_string(self) -> None:
        """Returns None for unknown string."""
        manager = ServiceTypeManager()

        result = manager.string_to_service_type("unknown_type")

        assert result is None

    def test_returns_none_for_empty_string(self) -> None:
        """Returns None for empty string."""
        manager = ServiceTypeManager()

        result = manager.string_to_service_type("")

        assert result is None

    def test_does_not_convert_unknown_enum_value(self) -> None:
        """Does not convert 'unknown' to ServiceType.UNKNOWN."""
        manager = ServiceTypeManager()

        result = manager.string_to_service_type("unknown")

        assert result is None
