"""Tests for optimized_status_reporter_mixins module."""

from unittest.mock import MagicMock, Mock

import pytest

from common.optimized_status_reporter_mixins import (
    StatusReporterFormatterMixin,
    StatusReporterWeatherMixin,
    _ensure_str_list,
    _generate_weather_lines,
)


class TestEnsureStrList:
    """Tests for _ensure_str_list helper function."""

    def test_none_returns_empty_list(self):
        """Test that None returns empty list."""
        assert _ensure_str_list(None) == []

    def test_list_of_strings_converted(self):
        """Test that list of strings is converted."""
        result = _ensure_str_list(["a", "b", "c"])
        assert result == ["a", "b", "c"]

    def test_list_of_ints_converted_to_strings(self):
        """Test that list of ints is converted to strings."""
        result = _ensure_str_list([1, 2, 3])
        assert result == ["1", "2", "3"]

    def test_single_string_converted_to_char_list(self):
        """Test that single string is converted to char list."""
        result = _ensure_str_list("hello")
        assert result == ["h", "e", "l", "l", "o"]

    def test_single_int_wrapped_and_converted(self):
        """Test that single int is wrapped and converted."""
        result = _ensure_str_list(42)
        assert result == ["42"]

    def test_tuple_converted_to_list(self):
        """Test that tuple is converted to list."""
        result = _ensure_str_list(("x", "y", "z"))
        assert result == ["x", "y", "z"]

    def test_generator_converted_to_list(self):
        """Test that generator is converted to list."""
        result = _ensure_str_list(x for x in ["a", "b"])
        assert result == ["a", "b"]


class TestGenerateWeatherLines:
    """Tests for _generate_weather_lines helper function."""

    def test_printer_with_generate_weather_section_method(self):
        """Test printer with generate_weather_section method (non-Mock)."""

        class RealPrinter:
            def generate_weather_section(self, temps):
                return ["Line 1", "Line 2"]

        printer = RealPrinter()
        temperatures = {"NYC": 72}

        result = _generate_weather_lines(printer, temperatures)

        assert result == ["Line 1", "Line 2"]

    def test_printer_with_mock_generate_method_uses_weather_generator(self):
        """Test that Mock generate_weather_section is skipped for _weather_generator."""
        printer = MagicMock()
        printer.generate_weather_section = Mock()
        weather_gen = MagicMock()
        weather_gen.generate_weather_section = MagicMock(return_value=["Generator Line"])
        printer._weather_generator = weather_gen
        temperatures = {"LA": 85}

        result = _generate_weather_lines(printer, temperatures)

        assert result == ["Generator Line"]
        weather_gen.generate_weather_section.assert_called_once_with(temperatures)

    def test_printer_with_weather_generator_attribute(self):
        """Test printer with _weather_generator attribute."""
        printer = MagicMock()
        del printer.generate_weather_section
        weather_gen = MagicMock()
        weather_gen.generate_weather_section = MagicMock(return_value=["Gen Line"])
        printer._weather_generator = weather_gen
        temperatures = {"CHI": 60}

        result = _generate_weather_lines(printer, temperatures)

        assert result == ["Gen Line"]
        weather_gen.generate_weather_section.assert_called_once_with(temperatures)

    def test_printer_with_callable_mock_as_fallback(self):
        """Test printer with callable Mock as fallback."""
        printer = MagicMock()
        printer.generate_weather_section = Mock(return_value=["Mock Line"])
        printer._weather_generator = None
        temperatures = {"BOS": 55}

        result = _generate_weather_lines(printer, temperatures)

        assert result == ["Mock Line"]
        printer.generate_weather_section.assert_called_once_with(temperatures)

    def test_printer_without_methods_returns_empty(self):
        """Test printer without required methods returns empty list."""
        printer = MagicMock()
        del printer.generate_weather_section
        printer._weather_generator = None
        temperatures = {"SF": 65}

        result = _generate_weather_lines(printer, temperatures)

        assert result == []

    def test_printer_with_non_callable_generate_method(self):
        """Test printer with non-callable generate method."""
        printer = MagicMock()
        printer.generate_weather_section = "not callable"
        printer._weather_generator = None
        temperatures = {"SEA": 50}

        result = _generate_weather_lines(printer, temperatures)

        assert result == []


class TestStatusReporterWeatherMixin:
    """Tests for StatusReporterWeatherMixin."""

    def test_generate_weather_section_with_temperatures(self):
        """Test _generate_weather_section with weather_temperatures."""

        class RealPrinter:
            def generate_weather_section(self, temps):
                return ["Weather Line 1"]

        class TestReporter(StatusReporterWeatherMixin):
            def __init__(self):
                self._printer = RealPrinter()

        reporter = TestReporter()
        status_data = {"weather_temperatures": {"NYC": 72, "LA": 85}}

        result = reporter._generate_weather_section(status_data)

        assert result == ["Weather Line 1"]

    def test_generate_weather_section_without_temperatures(self):
        """Test _generate_weather_section without weather_temperatures."""

        class RealPrinter:
            def generate_weather_section(self, temps):
                return ["Empty Weather"]

        class TestReporter(StatusReporterWeatherMixin):
            def __init__(self):
                self._printer = RealPrinter()

        reporter = TestReporter()
        status_data = {}

        result = reporter._generate_weather_section(status_data)

        assert result == ["Empty Weather"]

    def test_generate_weather_section_with_none_temperatures(self):
        """Test _generate_weather_section with None temperatures."""

        class RealPrinter:
            def generate_weather_section(self, temps):
                return ["None Weather"]

        class TestReporter(StatusReporterWeatherMixin):
            def __init__(self):
                self._printer = RealPrinter()

        reporter = TestReporter()
        status_data = {"weather_temperatures": None}

        result = reporter._generate_weather_section(status_data)

        assert result == ["None Weather"]


class TestStatusReporterFormatterMixin:
    """Tests for StatusReporterFormatterMixin."""

    def test_format_log_activity_short(self):
        """Test format_log_activity_short delegates to formatter."""

        class TestReporter(StatusReporterFormatterMixin):
            def __init__(self):
                self._log_activity_formatter = MagicMock()
                self._log_activity_formatter.format_log_activity_short = MagicMock(return_value="formatted")

        reporter = TestReporter()
        activity = {"action": "test"}

        result = reporter.format_log_activity_short("service1", activity)

        assert result == "formatted"
        reporter._log_activity_formatter.format_log_activity_short.assert_called_once_with("service1", activity)

    def test_format_log_activity_short_with_none(self):
        """Test format_log_activity_short with None activity."""

        class TestReporter(StatusReporterFormatterMixin):
            def __init__(self):
                self._log_activity_formatter = MagicMock()
                self._log_activity_formatter.format_log_activity_short = MagicMock(return_value=None)

        reporter = TestReporter()

        result = reporter.format_log_activity_short("service2", None)

        assert result is None
        reporter._log_activity_formatter.format_log_activity_short.assert_called_once_with("service2", None)

    def test_format_log_activity_short_backward_compatible_alias(self):
        """Test _format_log_activity_short is backward-compatible alias."""

        class TestReporter(StatusReporterFormatterMixin):
            def __init__(self):
                self._log_activity_formatter = MagicMock()
                self._log_activity_formatter.format_log_activity_short = MagicMock(return_value="aliased")

        reporter = TestReporter()
        activity = {"action": "alias_test"}

        result = reporter._format_log_activity_short("service3", activity)

        assert result == "aliased"
        reporter._log_activity_formatter.format_log_activity_short.assert_called_once_with("service3", activity)
