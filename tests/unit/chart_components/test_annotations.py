"""Tests for chart_components.annotations module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from common.chart_components.annotations import (
    _build_sorted_dawn_dusk_lists,
    _chart_bounds,
    _next_dawn_after,
    _NightShadingContext,
    _shade_between_dusks_and_dawns,
    _shade_initial_gap,
    _timestamp_with_naive_datetime,
    add_dawn_dusk_shading,
    add_vertical_line_annotations,
)


class TestChartBounds:
    """Tests for _chart_bounds function."""

    def test_returns_bounds(self) -> None:
        """Test returns chart bounds."""
        now = datetime(2025, 1, 15, 12, 0, 0)
        later = datetime(2025, 1, 15, 18, 0, 0)

        start, end = _chart_bounds([now, later])

        assert start < end

    def test_single_timestamp(self) -> None:
        """Test with single timestamp."""
        now = datetime(2025, 1, 15, 12, 0, 0)

        start, end = _chart_bounds([now])

        assert start == end


class TestTimestampWithNaiveDatetime:
    """Tests for _timestamp_with_naive_datetime function."""

    def test_aware_datetime(self) -> None:
        """Test converts aware datetime to naive."""
        aware = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        num, naive = _timestamp_with_naive_datetime(aware)

        assert naive.tzinfo is None
        assert isinstance(num, float)

    def test_naive_datetime(self) -> None:
        """Test keeps naive datetime as is."""
        naive = datetime(2025, 1, 15, 12, 0, 0)

        num, result = _timestamp_with_naive_datetime(naive)

        assert result.tzinfo is None
        assert isinstance(num, float)


class TestBuildSortedDawnDuskLists:
    """Tests for _build_sorted_dawn_dusk_lists function."""

    def test_sorts_dawns_and_dusks(self) -> None:
        """Test sorts dawn and dusk lists."""
        dawn1 = datetime(2025, 1, 15, 6, 0, 0)
        dusk1 = datetime(2025, 1, 15, 18, 0, 0)
        dawn2 = datetime(2025, 1, 14, 6, 30, 0)
        dusk2 = datetime(2025, 1, 14, 17, 30, 0)

        dawns, dusks = _build_sorted_dawn_dusk_lists([(dawn1, dusk1), (dawn2, dusk2)])

        assert len(dawns) == 2
        assert len(dusks) == 2
        assert dawns[0][0] < dawns[1][0]
        assert dusks[0][0] < dusks[1][0]


class TestNightShadingContext:
    """Tests for _NightShadingContext class."""

    def test_first_shade_has_label(self) -> None:
        """Test first shade call has label."""
        mock_ax = MagicMock()
        ctx = _NightShadingContext(mock_ax)

        ctx.shade(0.0, 1.0)

        mock_ax.axvspan.assert_called_once()
        call_kwargs = mock_ax.axvspan.call_args[1]
        assert call_kwargs["label"] == "Night Hours"

    def test_second_shade_no_label(self) -> None:
        """Test second shade call has no label."""
        mock_ax = MagicMock()
        ctx = _NightShadingContext(mock_ax)

        ctx.shade(0.0, 1.0)
        ctx.shade(1.0, 2.0)

        assert mock_ax.axvspan.call_count == 2
        second_call_kwargs = mock_ax.axvspan.call_args_list[1][1]
        assert second_call_kwargs["label"] is None


class TestNextDawnAfter:
    """Tests for _next_dawn_after function."""

    def test_finds_next_dawn(self) -> None:
        """Test finds dawn after dusk."""
        dawns = [(1.0, datetime(2025, 1, 15, 6, 0, 0)), (2.0, datetime(2025, 1, 16, 6, 0, 0))]

        result = _next_dawn_after(dawns, 0.5)

        assert result is not None
        assert result[0] == 1.0

    def test_no_dawn_after(self) -> None:
        """Test returns None when no dawn after dusk."""
        dawns = [(1.0, datetime(2025, 1, 15, 6, 0, 0))]

        result = _next_dawn_after(dawns, 2.0)

        assert result is None

    def test_empty_dawns(self) -> None:
        """Test returns None with empty dawns."""
        result = _next_dawn_after([], 0.5)
        assert result is None


class TestShadeInitialGap:
    """Tests for _shade_initial_gap function."""

    def test_shades_when_dawn_after_start(self) -> None:
        """Test shades from chart start to first dawn."""
        mock_ax = MagicMock()
        ctx = _NightShadingContext(mock_ax)
        dawns = [(2.0, datetime(2025, 1, 15, 6, 0, 0))]

        _shade_initial_gap(ctx, dawns, 1.0)

        mock_ax.axvspan.assert_called_once()

    def test_no_shade_when_dawn_before_start(self) -> None:
        """Test no shade when first dawn before chart start."""
        mock_ax = MagicMock()
        ctx = _NightShadingContext(mock_ax)
        dawns = [(0.5, datetime(2025, 1, 15, 6, 0, 0))]

        _shade_initial_gap(ctx, dawns, 1.0)

        mock_ax.axvspan.assert_not_called()

    def test_no_shade_when_no_dawns(self) -> None:
        """Test no shade when no dawns."""
        mock_ax = MagicMock()
        ctx = _NightShadingContext(mock_ax)

        _shade_initial_gap(ctx, [], 1.0)

        mock_ax.axvspan.assert_not_called()


class TestShadeBetweenDusksAndDawns:
    """Tests for _shade_between_dusks_and_dawns function."""

    def test_shades_dusk_to_dawn(self) -> None:
        """Test shades from dusk to next dawn."""
        mock_ax = MagicMock()
        ctx = _NightShadingContext(mock_ax)
        dawns = [(2.0, datetime(2025, 1, 16, 6, 0, 0))]
        dusks = [(1.0, datetime(2025, 1, 15, 18, 0, 0))]

        _shade_between_dusks_and_dawns(ctx, dawns, dusks, 3.0)

        mock_ax.axvspan.assert_called_once()

    def test_shades_dusk_to_end_when_no_dawn(self) -> None:
        """Test shades from dusk to chart end when no next dawn."""
        mock_ax = MagicMock()
        ctx = _NightShadingContext(mock_ax)
        dusks = [(1.0, datetime(2025, 1, 15, 18, 0, 0))]

        _shade_between_dusks_and_dawns(ctx, [], dusks, 2.0)

        mock_ax.axvspan.assert_called_once()


class TestAddDawnDuskShading:
    """Tests for add_dawn_dusk_shading function."""

    def test_no_shading_when_no_periods(self) -> None:
        """Test no shading when no periods."""
        mock_ax = MagicMock()

        add_dawn_dusk_shading(mock_ax, None, [datetime.now()])

        mock_ax.axvspan.assert_not_called()

    def test_no_shading_when_no_timestamps(self) -> None:
        """Test no shading when no timestamps."""
        mock_ax = MagicMock()
        dawn = datetime(2025, 1, 15, 6, 0, 0)
        dusk = datetime(2025, 1, 15, 18, 0, 0)

        add_dawn_dusk_shading(mock_ax, [(dawn, dusk)], None)

        mock_ax.axvspan.assert_not_called()

    def test_adds_shading(self) -> None:
        """Test adds dawn dusk shading."""
        mock_ax = MagicMock()
        dawn = datetime(2025, 1, 15, 6, 0, 0)
        dusk = datetime(2025, 1, 15, 18, 0, 0)
        timestamps = [datetime(2025, 1, 15, 0, 0, 0), datetime(2025, 1, 15, 23, 59, 59)]

        add_dawn_dusk_shading(mock_ax, [(dawn, dusk)], timestamps)

        assert mock_ax.axvspan.call_count >= 1


class TestAddVerticalLineAnnotations:
    """Tests for add_vertical_line_annotations function."""

    def test_no_lines_when_none(self) -> None:
        """Test no lines when vertical_lines is None."""
        mock_ax = MagicMock()

        add_vertical_line_annotations(mock_ax, None, is_temperature_chart=False, local_timezone=None)

        mock_ax.axvline.assert_not_called()

    def test_no_lines_when_empty(self) -> None:
        """Test no lines when vertical_lines is empty."""
        mock_ax = MagicMock()

        add_vertical_line_annotations(mock_ax, [], is_temperature_chart=False, local_timezone=None)

        mock_ax.axvline.assert_not_called()

    def test_adds_vertical_line(self) -> None:
        """Test adds vertical line."""
        mock_ax = MagicMock()
        line = (datetime(2025, 1, 15, 12, 0, 0), "orange", "Solar Noon")

        add_vertical_line_annotations(mock_ax, [line], is_temperature_chart=False, local_timezone=None)

        mock_ax.axvline.assert_called_once()

    def test_midnight_line_style(self) -> None:
        """Test midnight line has special style."""
        mock_ax = MagicMock()
        line = (datetime(2025, 1, 15, 0, 0, 0), "blue", "Midnight")

        add_vertical_line_annotations(mock_ax, [line], is_temperature_chart=False, local_timezone=None)

        call_kwargs = mock_ax.axvline.call_args[1]
        assert call_kwargs["color"] == "blue"
        assert call_kwargs["linewidth"] == 3

    def test_temperature_chart_with_timezone(self) -> None:
        """Test converts to local timezone for temperature chart."""
        mock_ax = MagicMock()
        line = (datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc), "orange", "Solar Noon")
        local_tz = ZoneInfo("America/New_York")

        add_vertical_line_annotations(mock_ax, [line], is_temperature_chart=True, local_timezone=local_tz)

        mock_ax.axvline.assert_called_once()

    def test_temperature_chart_with_naive_datetime(self) -> None:
        """Test handles naive datetime in temperature chart."""
        mock_ax = MagicMock()
        line = (datetime(2025, 1, 15, 12, 0, 0), "orange", "Solar Noon")
        local_tz = ZoneInfo("America/New_York")

        add_vertical_line_annotations(mock_ax, [line], is_temperature_chart=True, local_timezone=local_tz)

        mock_ax.axvline.assert_called_once()

    def test_non_temperature_chart_aware_datetime(self) -> None:
        """Test removes tzinfo for non-temperature chart."""
        mock_ax = MagicMock()
        line = (datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc), "orange", "Solar Noon")

        add_vertical_line_annotations(mock_ax, [line], is_temperature_chart=False, local_timezone=None)

        mock_ax.axvline.assert_called_once()
