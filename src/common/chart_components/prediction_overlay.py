from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence

import matplotlib.colors as mcolors
import matplotlib.dates as mdates
import numpy as np

from .time_conversions import ensure_naive_timestamps


@dataclass(frozen=True)
class PredictionOverlayResult:
    """Summarizes the extrema contributed by the prediction overlay."""

    extrema: List[float]


def _extract_historical_anchor(
    historical_timestamps: Sequence[datetime],
    historical_values: Sequence[float],
) -> tuple[Optional[float], Optional[float]]:
    """Return the numeric timestamp and value that anchor the prediction bridge."""
    if not historical_timestamps:
        return None, None

    last_timestamp = historical_timestamps[-1]
    if last_timestamp.tzinfo is not None:
        last_timestamp = last_timestamp.replace(tzinfo=None)
    anchor_numeric = float(mdates.date2num(last_timestamp))

    last_value = float(historical_values[-1]) if historical_values else None
    return anchor_numeric, last_value


def _merge_prediction_series(
    anchor_numeric: Optional[float],
    anchor_value: Optional[float],
    prediction_numeric: np.ndarray,
    prediction_values: Sequence[float],
) -> tuple[np.ndarray, np.ndarray]:
    """Return numeric/time-aligned arrays that connect history with predictions."""
    prediction_array = np.asarray(prediction_values, dtype=float)
    if anchor_numeric is None:
        return prediction_numeric, prediction_array

    seed_value = anchor_value if anchor_value is not None else float(prediction_values[0])
    merged_numeric = np.concatenate(([anchor_numeric], prediction_numeric))
    merged_values = np.concatenate(([seed_value], prediction_array))
    return merged_numeric, merged_values


def _draw_prediction_line(ax, numeric: np.ndarray, values: np.ndarray, color: str) -> None:
    """Plot the primary prediction line onto the supplied axis."""
    ax.plot(
        numeric,
        values,
        color=color,
        linewidth=2,
        linestyle="--",
        alpha=0.9,
        zorder=5,
        label="Predicted Path",
    )


def _validate_uncertainty_inputs(
    prediction_values: Sequence[float], prediction_uncertainties: Sequence[float]
) -> None:
    if len(prediction_uncertainties) != len(prediction_values):
        raise ValueError("prediction_uncertainties must match prediction_values length")


@dataclass(frozen=True)
class UncertaintyEnvelopeParams:
    """Parameters for rendering uncertainty envelopes."""

    anchor_numeric: Optional[float]
    prediction_numeric: np.ndarray
    merged_numeric: np.ndarray
    merged_values: np.ndarray
    prediction_values: Sequence[float]
    prediction_uncertainties: Sequence[float]
    plot_color: str


def _render_uncertainty_envelopes(
    ax,
    params: UncertaintyEnvelopeParams,
) -> List[float]:
    """Draw ±1σ and ±2σ bands and return the extrema contributed by uncertainty."""
    _validate_uncertainty_inputs(params.prediction_values, params.prediction_uncertainties)

    sigma = _build_sigma_array(params.anchor_numeric, params.prediction_uncertainties)
    numeric, values = _resolve_plot_series(
        params.anchor_numeric,
        params.prediction_numeric,
        params.merged_numeric,
        params.merged_values,
        params.prediction_values,
    )
    colors = _build_envelope_colors(params.plot_color)
    envelopes = _compute_envelope_bounds(values, sigma)
    _plot_uncertainty_bands(ax, numeric, envelopes, colors, params.plot_color)
    return _collect_uncertainty_extrema(params.prediction_values, params.prediction_uncertainties)


def _build_sigma_array(anchor_numeric: Optional[float], prediction_uncertainties: Sequence[float]):
    sigma = np.concatenate(([0.0], prediction_uncertainties))
    return sigma if anchor_numeric is not None else sigma[1:]


def _resolve_plot_series(
    anchor_numeric,
    prediction_numeric: np.ndarray,
    merged_numeric: np.ndarray,
    merged_values: np.ndarray,
    prediction_values: Sequence[float],
):
    if anchor_numeric is None:
        numeric = prediction_numeric
        values = np.asarray(prediction_values, dtype=float)
    else:
        numeric = merged_numeric
        values = merged_values
    return numeric, values


def _build_envelope_colors(plot_color: str):
    base_rgb = mcolors.to_rgb(plot_color)
    sigma1_rgb = tuple(0.7 * channel + 0.3 for channel in base_rgb)
    sigma2_rgb = mcolors.to_rgb("#475569")
    return {
        "sigma1_fill": (sigma1_rgb[0], sigma1_rgb[1], sigma1_rgb[2], 0.30),
        "sigma2_fill": (sigma2_rgb[0], sigma2_rgb[1], sigma2_rgb[2], 0.18),
        "sigma2_line": "#475569",
    }


def _compute_envelope_bounds(values: np.ndarray, sigma: np.ndarray):
    return {
        "sigma1_upper": values + sigma,
        "sigma1_lower": values - sigma,
        "sigma2_upper": values + 2.0 * sigma,
        "sigma2_lower": values - 2.0 * sigma,
    }


def _plot_uncertainty_bands(ax, numeric, envelopes, colors, plot_color: str) -> None:
    ax.fill_between(
        numeric,
        envelopes["sigma2_lower"],
        envelopes["sigma2_upper"],
        color=colors["sigma2_fill"],
        zorder=2,
        label="±2σ",
    )
    ax.fill_between(
        numeric,
        envelopes["sigma1_lower"],
        envelopes["sigma1_upper"],
        color=colors["sigma1_fill"],
        zorder=3,
        label="±1σ",
    )
    ax.plot(
        numeric,
        envelopes["sigma1_upper"],
        color=plot_color,
        linewidth=1.1,
        alpha=0.7,
        linestyle=":",
    )
    ax.plot(
        numeric,
        envelopes["sigma1_lower"],
        color=plot_color,
        linewidth=1.1,
        alpha=0.7,
        linestyle=":",
    )
    ax.plot(
        numeric,
        envelopes["sigma2_upper"],
        color=colors["sigma2_line"],
        linewidth=1.0,
        alpha=0.6,
        linestyle="--",
    )
    ax.plot(
        numeric,
        envelopes["sigma2_lower"],
        color=colors["sigma2_line"],
        linewidth=1.0,
        alpha=0.6,
        linestyle="--",
    )


def _collect_uncertainty_extrema(
    prediction_values: Sequence[float], prediction_uncertainties: Sequence[float]
) -> List[float]:
    extrema: List[float] = []
    for value, uncertainty in zip(prediction_values, prediction_uncertainties):
        extrema.extend([value + uncertainty, value - uncertainty])
    return extrema


def render_prediction_overlay(
    ax,
    historical_timestamps: Sequence[datetime],
    historical_values: Sequence[float],
    prediction_timestamps: Optional[Sequence[datetime]],
    prediction_values: Optional[Sequence[float]],
    prediction_uncertainties: Optional[Sequence[float]],
    plot_color: str,
) -> PredictionOverlayResult:
    """
    Plot the prediction path and uncertainty envelopes onto an axis.

    Args:
        ax: Matplotlib axis to draw on.
        historical_timestamps: Naive timestamps for historical data.
        historical_values: Historical values aligned with timestamps.
        prediction_timestamps: Future timestamps for predictions (naive).
        prediction_values: Predicted values aligned with prediction timestamps.
        prediction_uncertainties: Optional standard deviations.
        plot_color: Base color for the prediction line.

    Returns:
        PredictionOverlayResult capturing extrema contributed by the overlay.
    """
    if not prediction_timestamps or not prediction_values:
        return PredictionOverlayResult(extrema=[])

    if len(prediction_timestamps) != len(prediction_values):
        raise ValueError("prediction_timestamps and prediction_values must have the same length")

    anchor_numeric, anchor_value = _extract_historical_anchor(
        historical_timestamps, historical_values
    )
    prediction_numeric = mdates.date2num(prediction_timestamps)
    merged_numeric, merged_values = _merge_prediction_series(
        anchor_numeric, anchor_value, prediction_numeric, prediction_values
    )

    _draw_prediction_line(ax, merged_numeric, merged_values, plot_color)

    extrema: List[float] = list(prediction_values)
    if prediction_uncertainties:
        envelope_params = UncertaintyEnvelopeParams(
            anchor_numeric=anchor_numeric,
            prediction_numeric=prediction_numeric,
            merged_numeric=merged_numeric,
            merged_values=merged_values,
            prediction_values=prediction_values,
            prediction_uncertainties=prediction_uncertainties,
            plot_color=plot_color,
        )
        extrema.extend(
            _render_uncertainty_envelopes(
                ax,
                envelope_params,
            )
        )

    return PredictionOverlayResult(extrema=extrema)


@dataclass(frozen=True)
class PredictionOverlayParams:
    """Parameters for prediction overlay rendering."""

    historical_naive: Sequence[datetime]
    historical_values: Sequence[float]
    precomputed_prediction: Optional[Sequence[datetime]]
    prediction_timestamps: Optional[Sequence[datetime]]
    prediction_values: Optional[Sequence[float]]
    prediction_uncertainties: Optional[Sequence[float]]
    plot_color: str


def render_prediction_overlay_if_needed(
    *,
    ax,
    params: PredictionOverlayParams,
) -> PredictionOverlayResult:
    """
    Render a prediction overlay when prediction inputs are present.

    Args:
        ax: Matplotlib axis to draw on.
        params: Parameters for rendering prediction overlay.

    Returns:
        A PredictionOverlayResult capturing prediction extrema.
    """
    if not params.prediction_timestamps or not params.prediction_values:
        return PredictionOverlayResult(extrema=[])

    prediction_naive = (
        list(params.precomputed_prediction)
        if params.precomputed_prediction is not None
        else ensure_naive_timestamps(params.prediction_timestamps)
    )

    return render_prediction_overlay(
        ax=ax,
        historical_timestamps=params.historical_naive,
        historical_values=params.historical_values,
        prediction_timestamps=prediction_naive,
        prediction_values=params.prediction_values,
        prediction_uncertainties=params.prediction_uncertainties,
        plot_color=params.plot_color,
    )


def collect_prediction_extrema(
    overlay_result: PredictionOverlayResult,
    prediction_values: Optional[Sequence[float]],
    prediction_uncertainties: Optional[Sequence[float]],
) -> List[float]:
    """
    Calculate extrema contributed by a prediction overlay for axis scaling.

    Args:
        overlay_result: Result returned from the overlay render helper.
        prediction_values: Predicted point estimates.
        prediction_uncertainties: Optional predictive standard deviations.

    Returns:
        A list containing extrema to consider when computing axis limits.
    """
    if overlay_result.extrema:
        return list(overlay_result.extrema)

    extras: List[float] = []
    if prediction_values:
        extras.extend(prediction_values)
        if prediction_uncertainties:
            extras.extend([p + u for p, u in zip(prediction_values, prediction_uncertainties)])
            extras.extend([p - u for p, u in zip(prediction_values, prediction_uncertainties)])
    return extras
