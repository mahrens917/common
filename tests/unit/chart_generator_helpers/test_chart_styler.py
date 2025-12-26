"""Tests for chart_styler module."""

import pytest

from common.chart_generator_helpers.chart_styler import ChartStyler


class TestChartStyler:
    """Tests for ChartStyler class."""

    def test_init_sets_dimensions(self) -> None:
        """Test initialization sets chart dimensions."""
        styler = ChartStyler()

        assert styler.chart_width_inches == 12
        assert styler.chart_height_inches == 6
        assert styler.dpi == 150

    def test_init_sets_background_color(self) -> None:
        """Test initialization sets background color."""
        styler = ChartStyler()

        assert styler.background_color == "#f8f9fa"

    def test_init_sets_grid_color(self) -> None:
        """Test initialization sets grid color."""
        styler = ChartStyler()

        assert styler.grid_color == "#e9ecef"

    def test_init_sets_primary_color(self) -> None:
        """Test initialization sets primary color."""
        styler = ChartStyler()

        assert styler.primary_color == "#627EEA"

    def test_init_sets_secondary_color(self) -> None:
        """Test initialization sets secondary color."""
        styler = ChartStyler()

        assert styler.secondary_color == "#6c757d"

    def test_highlight_color_equals_primary(self) -> None:
        """Test highlight color equals primary color."""
        styler = ChartStyler()

        assert styler.highlight_color == styler.primary_color

    def test_init_sets_service_colors(self) -> None:
        """Test initialization sets service-specific colors."""
        styler = ChartStyler()

        assert styler.deribit_color == "#FF6B35"
        assert styler.kalshi_color == "#4ECDC4"
        assert styler.cpu_color == "#FF9500"
        assert styler.memory_color == "#627EEA"

    def test_multiple_instances_independent(self) -> None:
        """Test multiple instances are independent."""
        styler1 = ChartStyler()
        styler2 = ChartStyler()

        styler1.chart_width_inches = 20

        assert styler2.chart_width_inches == 12
