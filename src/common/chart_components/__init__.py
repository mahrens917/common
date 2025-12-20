"""Reusable helpers for unified chart generation."""

from .annotations import add_dawn_dusk_shading, add_vertical_line_annotations
from .prediction_overlay import (
    PredictionOverlayParams,
    PredictionOverlayResult,
    collect_prediction_extrema,
    render_prediction_overlay,
    render_prediction_overlay_if_needed,
)
from .time_conversions import (
    LocalizedTimestamps,
    build_axis_timestamps,
    ensure_naive_timestamps,
    localize_temperature_timestamps,
)
from .trade_visualization import annotate_trades_if_needed

__all__ = [
    "LocalizedTimestamps",
    "PredictionOverlayParams",
    "PredictionOverlayResult",
    "annotate_trades_if_needed",
    "add_dawn_dusk_shading",
    "add_vertical_line_annotations",
    "build_axis_timestamps",
    "collect_prediction_extrema",
    "ensure_naive_timestamps",
    "localize_temperature_timestamps",
    "render_prediction_overlay",
    "render_prediction_overlay_if_needed",
]
