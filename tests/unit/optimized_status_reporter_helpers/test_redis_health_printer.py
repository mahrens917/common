"""Tests for redis health printer module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from common.optimized_status_reporter_helpers.redis_health_printer import (
    RedisHealthPrinter,
)


class TestPrintRedisHealthSection:
    """Tests for print_redis_health_section method."""

    def test_prints_header(self) -> None:
        """Prints Redis health check header."""
        printer = RedisHealthPrinter()
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        status_data = {
            "redis_connection_healthy": True,
            "redis_health_check": None,
            "redis_deribit_keys": 100,
            "redis_kalshi_keys": 200,
            "redis_cfb_keys": 50,
            "redis_weather_keys": 25,
        }

        printer.print_redis_health_section(status_data)

        assert any("Redis Health Check" in str(line) for line in emitted)

    def test_calls_healthy_printer_when_connected(self) -> None:
        """Calls _print_healthy_redis when connection healthy."""
        printer = RedisHealthPrinter()
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        status_data = {
            "redis_connection_healthy": True,
            "redis_health_check": None,
            "redis_deribit_keys": 100,
            "redis_kalshi_keys": 200,
            "redis_cfb_keys": 50,
            "redis_weather_keys": 25,
        }

        printer.print_redis_health_section(status_data)

        assert any("🟢" in str(line) for line in emitted)

    def test_calls_failed_printer_when_disconnected(self) -> None:
        """Calls _print_failed_redis when connection unhealthy."""
        printer = RedisHealthPrinter()
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        status_data = {
            "redis_connection_healthy": False,
            "redis_health_check": None,
        }

        printer.print_redis_health_section(status_data)

        assert any("🔴" in str(line) for line in emitted)


class TestPrintHealthyRedis:
    """Tests for _print_healthy_redis method."""

    def test_prints_healthy_without_details(self) -> None:
        """Prints healthy message when no details available."""
        printer = RedisHealthPrinter()
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        status_data = {
            "redis_deribit_keys": 100,
            "redis_kalshi_keys": 200,
            "redis_cfb_keys": 50,
            "redis_weather_keys": 25,
        }

        printer._print_healthy_redis(None, status_data)

        assert any("Healthy" in str(line) for line in emitted)

    def test_prints_key_counts(self) -> None:
        """Prints all key counts."""
        printer = RedisHealthPrinter()
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        status_data = {
            "redis_deribit_keys": 100,
            "redis_kalshi_keys": 200,
            "redis_cfb_keys": 50,
            "redis_weather_keys": 25,
        }

        printer._print_healthy_redis(None, status_data)

        assert any("Deribit" in str(line) and "100" in str(line) for line in emitted)
        assert any("Kalshi" in str(line) and "200" in str(line) for line in emitted)
        assert any("CFB" in str(line) and "50" in str(line) for line in emitted)
        assert any("Weather" in str(line) and "25" in str(line) for line in emitted)

    def test_prints_degraded_status(self) -> None:
        """Prints slow/degraded status."""
        printer = RedisHealthPrinter()
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        health = MagicMock()
        health.details = {"ping_duration": 0.5}
        health.status.value = "degraded"

        status_data = {
            "redis_deribit_keys": 100,
            "redis_kalshi_keys": 200,
            "redis_cfb_keys": 50,
            "redis_weather_keys": 25,
        }

        printer._print_healthy_redis(health, status_data)

        assert any("Slow" in str(line) for line in emitted)

    def test_prints_pool_metrics(self) -> None:
        """Prints connection pool metrics."""
        printer = RedisHealthPrinter()
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        health = MagicMock()
        health.details = {
            "ping_duration": 0.01,
            "connection_pool_metrics": {"connection_reuse_rate": 0.95, "connection_errors": 0},
        }
        health.status.value = "healthy"

        status_data = {
            "redis_deribit_keys": 100,
            "redis_kalshi_keys": 200,
            "redis_cfb_keys": 50,
            "redis_weather_keys": 25,
        }

        printer._print_healthy_redis(health, status_data)

        assert any("Pool Reuse Rate" in str(line) for line in emitted)

    def test_prints_connection_errors(self) -> None:
        """Prints connection errors when present."""
        printer = RedisHealthPrinter()
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        health = MagicMock()
        health.details = {
            "ping_duration": 0.01,
            "connection_pool_metrics": {"connection_errors": 5, "connection_reuse_rate": 0.8},
        }
        health.status.value = "healthy"

        status_data = {
            "redis_deribit_keys": 100,
            "redis_kalshi_keys": 200,
            "redis_cfb_keys": 50,
            "redis_weather_keys": 25,
        }

        printer._print_healthy_redis(health, status_data)

        assert any("Connection Errors" in str(line) for line in emitted)


class TestPrintFailedRedis:
    """Tests for _print_failed_redis method."""

    def test_prints_failed_without_details(self) -> None:
        """Prints failed message when no details available."""
        printer = RedisHealthPrinter()
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        printer._print_failed_redis(None)

        assert any("Failed" in str(line) for line in emitted)
        assert any("🔴" in str(line) for line in emitted)

    def test_prints_timeout_details(self) -> None:
        """Prints timeout duration when available."""
        printer = RedisHealthPrinter()
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        health = MagicMock()
        health.details = {"timeout_duration": 5.0}
        health.message = "Connection timed out"

        printer._print_failed_redis(health)

        assert any("Timeout" in str(line) for line in emitted)

    def test_prints_error_type(self) -> None:
        """Prints error type when available."""
        printer = RedisHealthPrinter()
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        health = MagicMock()
        health.details = {"error_type": "ConnectionRefused"}
        health.message = "Connection refused"

        printer._print_failed_redis(health)

        assert any("ConnectionRefused" in str(line) for line in emitted)

    def test_prints_error_message(self) -> None:
        """Prints error message from health check."""
        printer = RedisHealthPrinter()
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        health = MagicMock()
        health.details = {"timeout_duration": 2.0}
        health.message = "Custom error message"

        printer._print_failed_redis(health)

        # Error message is printed after timeout info
        assert any("Custom error message" in str(line) for line in emitted)
