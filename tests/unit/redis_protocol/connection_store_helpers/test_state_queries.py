"""Tests for state query helpers."""

from __future__ import annotations

import time

from common.connection_state import ConnectionState
from common.redis_protocol.connection_store_helpers.state_processor import (
    ConnectionStateInfo,
)
from common.redis_protocol.connection_store_helpers.state_queries import (
    filter_reconnecting_services,
    is_reconnecting,
)


class TestIsReconnecting:
    """Tests for is_reconnecting function."""

    def test_returns_true_when_in_reconnection_flag(self) -> None:
        """Returns True when in_reconnection is True."""
        state_info = ConnectionStateInfo(
            service_name="test",
            state=ConnectionState.CONNECTED,
            timestamp=time.time(),
            in_reconnection=True,
        )

        assert is_reconnecting(state_info) is True

    def test_returns_true_when_state_reconnecting(self) -> None:
        """Returns True when state is RECONNECTING."""
        state_info = ConnectionStateInfo(
            service_name="test",
            state=ConnectionState.RECONNECTING,
            timestamp=time.time(),
            in_reconnection=False,
        )

        assert is_reconnecting(state_info) is True

    def test_returns_true_when_state_connecting(self) -> None:
        """Returns True when state is CONNECTING."""
        state_info = ConnectionStateInfo(
            service_name="test",
            state=ConnectionState.CONNECTING,
            timestamp=time.time(),
            in_reconnection=False,
        )

        assert is_reconnecting(state_info) is True

    def test_returns_false_when_connected(self) -> None:
        """Returns False when connected normally."""
        state_info = ConnectionStateInfo(
            service_name="test",
            state=ConnectionState.CONNECTED,
            timestamp=time.time(),
            in_reconnection=False,
        )

        assert is_reconnecting(state_info) is False

    def test_returns_false_when_disconnected(self) -> None:
        """Returns False when disconnected."""
        state_info = ConnectionStateInfo(
            service_name="test",
            state=ConnectionState.DISCONNECTED,
            timestamp=time.time(),
            in_reconnection=False,
        )

        assert is_reconnecting(state_info) is False


class TestFilterReconnectingServices:
    """Tests for filter_reconnecting_services function."""

    def test_returns_empty_when_no_services(self) -> None:
        """Returns empty list when no services."""
        result = filter_reconnecting_services({})

        assert result == []

    def test_returns_reconnecting_service(self) -> None:
        """Returns services that are reconnecting."""
        all_states = {
            "svc1": ConnectionStateInfo(
                service_name="svc1",
                state=ConnectionState.RECONNECTING,
                timestamp=time.time(),
                in_reconnection=False,
            ),
            "svc2": ConnectionStateInfo(
                service_name="svc2",
                state=ConnectionState.CONNECTED,
                timestamp=time.time(),
                in_reconnection=False,
            ),
        }

        result = filter_reconnecting_services(all_states)

        assert "svc1" in result
        assert "svc2" not in result

    def test_returns_multiple_reconnecting_services(self) -> None:
        """Returns all services that are reconnecting."""
        all_states = {
            "svc1": ConnectionStateInfo(
                service_name="svc1",
                state=ConnectionState.RECONNECTING,
                timestamp=time.time(),
                in_reconnection=False,
            ),
            "svc2": ConnectionStateInfo(
                service_name="svc2",
                state=ConnectionState.CONNECTING,
                timestamp=time.time(),
                in_reconnection=False,
            ),
            "svc3": ConnectionStateInfo(
                service_name="svc3",
                state=ConnectionState.CONNECTED,
                timestamp=time.time(),
                in_reconnection=False,
            ),
        }

        result = filter_reconnecting_services(all_states)

        assert len(result) == 2
        assert "svc1" in result
        assert "svc2" in result
