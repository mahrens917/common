"""Tests for unified_chart_params_builder module."""

from datetime import datetime, timezone

from common.chart_generator.renderers.unified_chart_params_builder import (
    build_unified_chart_params,
)

# Test constants
TEST_CHART_TITLE = "Test Chart"
TEST_Y_LABEL = "Test Y Label"
TEST_TIMESTAMP = datetime(2024, 12, 25, 12, 0, tzinfo=timezone.utc)
TEST_VALUE = 100.0


class TestBuildUnifiedChartParams:
    """Tests for build_unified_chart_params function."""

    def test_returns_unified_chart_params(self) -> None:
        """Test returns UnifiedChartParams instance."""
        result = build_unified_chart_params()

        assert result is not None
        assert hasattr(result, "timestamps")
        assert hasattr(result, "values")

    def test_sets_default_timestamps(self) -> None:
        """Test sets empty timestamps by default."""
        result = build_unified_chart_params()

        assert result.timestamps == []

    def test_sets_default_values(self) -> None:
        """Test sets empty values by default."""
        result = build_unified_chart_params()

        assert result.values == []

    def test_sets_default_chart_title(self) -> None:
        """Test sets empty chart_title by default."""
        result = build_unified_chart_params()

        assert result.chart_title == ""

    def test_sets_default_y_label(self) -> None:
        """Test sets empty y_label by default."""
        result = build_unified_chart_params()

        assert result.y_label == ""

    def test_passes_custom_timestamps(self) -> None:
        """Test passes custom timestamps."""
        timestamps = [TEST_TIMESTAMP]

        result = build_unified_chart_params(timestamps=timestamps)

        assert result.timestamps == timestamps

    def test_passes_custom_values(self) -> None:
        """Test passes custom values."""
        values = [TEST_VALUE]

        result = build_unified_chart_params(values=values)

        assert result.values == values

    def test_passes_custom_chart_title(self) -> None:
        """Test passes custom chart_title."""
        result = build_unified_chart_params(chart_title=TEST_CHART_TITLE)

        assert result.chart_title == TEST_CHART_TITLE

    def test_passes_custom_y_label(self) -> None:
        """Test passes custom y_label."""
        result = build_unified_chart_params(y_label=TEST_Y_LABEL)

        assert result.y_label == TEST_Y_LABEL

    def test_aliases_value_formatter_to_value_formatter_func(self) -> None:
        """Test aliases value_formatter to value_formatter_func."""

        def formatter(x: float) -> str:
            return str(x)

        result = build_unified_chart_params(value_formatter=formatter)

        assert result.value_formatter_func is formatter

    def test_value_formatter_func_takes_precedence(self) -> None:
        """Test value_formatter_func takes precedence over value_formatter."""

        def formatter1(x: float) -> str:
            return f"1: {x}"

        def formatter2(x: float) -> str:
            return f"2: {x}"

        result = build_unified_chart_params(
            value_formatter=formatter1,
            value_formatter_func=formatter2,
        )

        assert result.value_formatter_func is formatter2
