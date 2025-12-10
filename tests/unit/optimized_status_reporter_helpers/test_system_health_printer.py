"""Tests for system health printer module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from common.optimized_status_reporter_helpers.system_health_printer import (
    SystemHealthPrinter,
)


class TestSystemHealthPrinter:
    """Tests for SystemHealthPrinter class."""

    def test_init_stores_dependencies(self) -> None:
        """Stores data_coercion and data_formatting."""
        data_coercion = MagicMock()
        data_formatting = MagicMock()

        printer = SystemHealthPrinter(data_coercion, data_formatting)

        assert printer.data_coercion == data_coercion
        assert printer.data_formatting == data_formatting


class TestPrintSystemResourcesSection:
    """Tests for print_system_resources_section method."""

    def test_prints_header(self) -> None:
        """Prints system resources header."""
        data_coercion = MagicMock()
        data_formatting = MagicMock()
        printer = SystemHealthPrinter(data_coercion, data_formatting)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        health = MagicMock()
        health.status.value = "healthy"
        health.details = None
        health.message = "System resources normal"

        printer.print_system_resources_section(health)

        assert any("System Resources Health" in str(line) for line in emitted)

    def test_prints_failed_when_no_health(self) -> None:
        """Prints failed status when health is None."""
        data_coercion = MagicMock()
        data_formatting = MagicMock()
        printer = SystemHealthPrinter(data_coercion, data_formatting)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        printer.print_system_resources_section(None)

        assert any("Check Failed" in str(line) for line in emitted)
        assert any("🔴" in str(line) for line in emitted)

    def test_prints_healthy_status(self) -> None:
        """Prints healthy status with checkmark."""
        data_coercion = MagicMock()
        data_formatting = MagicMock()
        printer = SystemHealthPrinter(data_coercion, data_formatting)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        health = MagicMock()
        health.status.value = "healthy"
        health.details = None
        health.message = "System resources normal"

        printer.print_system_resources_section(health)

        assert any("✅" in str(line) for line in emitted)
        assert any("Healthy" in str(line) for line in emitted)

    def test_prints_degraded_status(self) -> None:
        """Prints degraded status with warning icon."""
        data_coercion = MagicMock()
        data_formatting = MagicMock()
        printer = SystemHealthPrinter(data_coercion, data_formatting)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        health = MagicMock()
        health.status.value = "degraded"
        health.details = None
        health.message = "High memory usage"

        printer.print_system_resources_section(health)

        assert any("⚠️" in str(line) for line in emitted)
        assert any("Degraded" in str(line) for line in emitted)

    def test_prints_unhealthy_status(self) -> None:
        """Prints unhealthy status with red icon."""
        data_coercion = MagicMock()
        data_formatting = MagicMock()
        printer = SystemHealthPrinter(data_coercion, data_formatting)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        health = MagicMock()
        health.status.value = "unhealthy"
        health.details = None
        health.message = "Critical resource usage"

        printer.print_system_resources_section(health)

        assert any("🔴" in str(line) for line in emitted)

    def test_prints_resource_details(self) -> None:
        """Prints CPU, memory, and disk usage details."""
        data_coercion = MagicMock()
        data_coercion.coerce_mapping.return_value = {
            "cpu_percent": 25.0,
            "memory_percent": 60.0,
            "disk_percent": 45.0,
        }
        data_formatting = MagicMock()
        data_formatting.format_percentage.side_effect = ["25.0%", "60.0%", "45.0%"]
        printer = SystemHealthPrinter(data_coercion, data_formatting)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        health = MagicMock()
        health.status.value = "healthy"
        health.details = {"cpu_percent": 25.0, "memory_percent": 60.0, "disk_percent": 45.0}
        health.message = "System resources normal"

        printer.print_system_resources_section(health)

        assert any("CPU Usage" in str(line) for line in emitted)
        assert any("Memory Usage" in str(line) for line in emitted)
        assert any("Disk Usage" in str(line) for line in emitted)

    def test_prints_issues_when_not_normal(self) -> None:
        """Prints issues when message is not normal."""
        data_coercion = MagicMock()
        data_formatting = MagicMock()
        printer = SystemHealthPrinter(data_coercion, data_formatting)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        health = MagicMock()
        health.status.value = "degraded"
        health.details = None
        health.message = "High CPU usage detected"

        printer.print_system_resources_section(health)

        assert any("Issues" in str(line) for line in emitted)
        assert any("High CPU usage detected" in str(line) for line in emitted)

    def test_does_not_print_issues_when_normal(self) -> None:
        """Does not print issues when message is normal."""
        data_coercion = MagicMock()
        data_formatting = MagicMock()
        printer = SystemHealthPrinter(data_coercion, data_formatting)
        emitted = []
        printer._emit_status_line = lambda x="": emitted.append(x)

        health = MagicMock()
        health.status.value = "healthy"
        health.details = None
        health.message = "System resources normal"

        printer.print_system_resources_section(health)

        assert not any("Issues" in str(line) for line in emitted)
