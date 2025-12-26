"""Tests for shading_renderer module."""

from datetime import datetime
from unittest.mock import MagicMock

from common.chart_components.annotations_helpers.shading_renderer import (
    _create_shading_function,
    render_nighttime_shading,
)


class TestCreateShadingFunction:
    """Tests for _create_shading_function."""

    def test_first_shade_applies_label(self) -> None:
        """Test that first shade call applies label."""
        mock_ax = MagicMock()
        label_ref = [False]
        shade = _create_shading_function(mock_ax, label_ref)

        shade(0.0, 1.0)

        mock_ax.axvspan.assert_called_once()
        call_kwargs = mock_ax.axvspan.call_args[1]
        assert call_kwargs["label"] == "Night Hours"
        assert label_ref[0] is True

    def test_subsequent_shade_no_label(self) -> None:
        """Test that subsequent shade calls have no label."""
        mock_ax = MagicMock()
        label_ref = [True]
        shade = _create_shading_function(mock_ax, label_ref)

        shade(0.0, 1.0)

        call_kwargs = mock_ax.axvspan.call_args[1]
        assert call_kwargs["label"] is None

    def test_shade_uses_correct_params(self) -> None:
        """Test shade uses correct axvspan parameters."""
        mock_ax = MagicMock()
        shade = _create_shading_function(mock_ax, [False])

        shade(1.5, 2.5)

        mock_ax.axvspan.assert_called_once()
        call_args = mock_ax.axvspan.call_args
        assert call_args[0][0] == 1.5
        assert call_args[0][1] == 2.5
        assert call_args[1]["alpha"] == 0.15
        assert call_args[1]["color"] == "gray"
        assert call_args[1]["zorder"] == 1


class TestRenderNighttimeShading:
    """Tests for render_nighttime_shading function."""

    def test_empty_dawns_and_dusks(self) -> None:
        """Test with empty dawn and dusk lists."""
        mock_ax = MagicMock()
        render_nighttime_shading(mock_ax, [], [], 0.0, 10.0)
        mock_ax.axvspan.assert_not_called()

    def test_shades_from_chart_start_to_first_dawn(self) -> None:
        """Test shading from chart start to first dawn."""
        mock_ax = MagicMock()
        dawns = [(5.0, datetime(2024, 1, 1, 6, 0))]
        dusks = []

        render_nighttime_shading(mock_ax, dawns, dusks, 0.0, 10.0)

        mock_ax.axvspan.assert_called_once()
        call_args = mock_ax.axvspan.call_args[0]
        assert call_args[0] == 0.0
        assert call_args[1] == 5.0

    def test_shades_dusk_to_next_dawn(self) -> None:
        """Test shading from dusk to next dawn."""
        mock_ax = MagicMock()
        dawns = [(6.0, datetime(2024, 1, 2, 6, 0))]
        dusks = [(4.0, datetime(2024, 1, 1, 20, 0))]

        render_nighttime_shading(mock_ax, dawns, dusks, 0.0, 10.0)

        assert mock_ax.axvspan.call_count >= 1

    def test_shades_dusk_to_chart_end(self) -> None:
        """Test shading from dusk to chart end when no next dawn."""
        mock_ax = MagicMock()
        dawns = []
        dusks = [(5.0, datetime(2024, 1, 1, 20, 0))]

        render_nighttime_shading(mock_ax, dawns, dusks, 0.0, 10.0)

        mock_ax.axvspan.assert_called_once()
        call_args = mock_ax.axvspan.call_args[0]
        assert call_args[0] == 5.0
        assert call_args[1] == 10.0

    def test_no_shade_when_dusk_after_chart_end(self) -> None:
        """Test no shading when dusk is after chart end and no dawn."""
        mock_ax = MagicMock()
        dawns = []
        dusks = [(15.0, datetime(2024, 1, 1, 20, 0))]

        render_nighttime_shading(mock_ax, dawns, dusks, 0.0, 10.0)

        mock_ax.axvspan.assert_not_called()
