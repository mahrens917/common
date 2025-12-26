"""Tests for chart_generator_helpers.chart_title_formatter module."""

import pytest

from common.chart_generator_helpers.chart_title_formatter import ChartTitleFormatter


class TestChartTitleFormatterFormatLoadChartTitle:
    """Tests for format_load_chart_title method."""

    def test_formats_deribit_title(self) -> None:
        """Test formats Deribit load chart title."""
        formatter = ChartTitleFormatter()

        result = formatter.format_load_chart_title("deribit")

        assert result == "Deribit Updates / min"

    def test_formats_deribit_uppercase(self) -> None:
        """Test formats Deribit title with uppercase."""
        formatter = ChartTitleFormatter()

        result = formatter.format_load_chart_title("DERIBIT")

        assert result == "Deribit Updates / min"

    def test_formats_kalshi_title(self) -> None:
        """Test formats Kalshi load chart title."""
        formatter = ChartTitleFormatter()

        result = formatter.format_load_chart_title("kalshi")

        assert result == "Kalshi Updates / min"

    def test_formats_kalshi_uppercase(self) -> None:
        """Test formats Kalshi title with uppercase."""
        formatter = ChartTitleFormatter()

        result = formatter.format_load_chart_title("KALSHI")

        assert result == "Kalshi Updates / min"

    def test_formats_other_service(self) -> None:
        """Test formats other service name."""
        formatter = ChartTitleFormatter()

        result = formatter.format_load_chart_title("binance")

        assert result == "Binance Updates / min"

    def test_formats_multi_word_service(self) -> None:
        """Test formats multi-word service name."""
        formatter = ChartTitleFormatter()

        result = formatter.format_load_chart_title("my_service")

        assert result == "My_Service Updates / min"


class TestChartTitleFormatterFormatSystemChartTitle:
    """Tests for format_system_chart_title method."""

    def test_formats_cpu_title(self) -> None:
        """Test formats CPU chart title."""
        formatter = ChartTitleFormatter()

        result = formatter.format_system_chart_title("cpu")

        assert result == "CPU (per minute)"

    def test_formats_memory_title(self) -> None:
        """Test formats memory chart title."""
        formatter = ChartTitleFormatter()

        result = formatter.format_system_chart_title("memory")

        assert result == "Memory (per minute)"

    def test_formats_other_metric_as_memory(self) -> None:
        """Test formats other metric as memory."""
        formatter = ChartTitleFormatter()

        result = formatter.format_system_chart_title("disk")

        assert result == "Memory (per minute)"


class TestChartTitleFormatterFormatPriceChartTitle:
    """Tests for format_price_chart_title method."""

    def test_formats_integer_price(self) -> None:
        """Test formats integer price."""
        formatter = ChartTitleFormatter()

        result = formatter.format_price_chart_title("BTC", 50000.0)

        assert result == "BTC Price History (Current: $50,000)"

    def test_formats_decimal_price(self) -> None:
        """Test formats decimal price."""
        formatter = ChartTitleFormatter()

        result = formatter.format_price_chart_title("ETH", 3500.55)

        assert result == "ETH Price History (Current: $3,500.55)"

    def test_formats_large_price(self) -> None:
        """Test formats large price."""
        formatter = ChartTitleFormatter()

        result = formatter.format_price_chart_title("BTC", 100000.0)

        assert result == "BTC Price History (Current: $100,000)"

    def test_formats_small_price(self) -> None:
        """Test formats small price."""
        formatter = ChartTitleFormatter()

        result = formatter.format_price_chart_title("DOGE", 0.15)

        assert result == "DOGE Price History (Current: $0.15)"
