"""Helper functions for prediction overlay rendering."""

from typing import List, Optional, Sequence

import matplotlib.colors as mcolors
import numpy as np


def prepare_sigma_array(
    anchor_numeric: Optional[float], prediction_uncertainties: Sequence[float]
) -> np.ndarray:
    """Prepare sigma array for uncertainty bands."""
    sigma = np.concatenate(([0.0], prediction_uncertainties))
    if anchor_numeric is None:
        sigma = sigma[1:]
    return sigma


def compute_band_colors(plot_color: str) -> tuple:
    """Compute colors for sigma bands."""
    base_rgb = mcolors.to_rgb(plot_color)
    sigma1_rgb = tuple(0.7 * channel + 0.3 for channel in base_rgb)
    sigma2_rgb = mcolors.to_rgb("#475569")
    sigma1_color = (sigma1_rgb[0], sigma1_rgb[1], sigma1_rgb[2], 0.30)
    sigma2_color = (sigma2_rgb[0], sigma2_rgb[1], sigma2_rgb[2], 0.18)
    return sigma1_color, sigma2_color


def select_numeric_and_values(
    anchor_numeric: Optional[float],
    prediction_numeric: np.ndarray,
    prediction_values: Sequence[float],
    merged_numeric: np.ndarray,
    merged_values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Select appropriate numeric and value arrays based on anchor."""
    if anchor_numeric is None:
        return prediction_numeric, np.asarray(prediction_values, dtype=float)
    return merged_numeric, merged_values


def draw_uncertainty_bands(
    ax,
    numeric: np.ndarray,
    values: np.ndarray,
    sigma: np.ndarray,
    sigma1_color,
    sigma2_color,
    plot_color: str,
):
    """Draw filled uncertainty bands and boundary lines."""
    sigma1_upper = values + sigma
    sigma1_lower = values - sigma
    sigma2_upper = values + 2.0 * sigma
    sigma2_lower = values - 2.0 * sigma

    ax.fill_between(numeric, sigma2_lower, sigma2_upper, color=sigma2_color, zorder=2, label="±2σ")
    ax.fill_between(numeric, sigma1_lower, sigma1_upper, color=sigma1_color, zorder=3, label="±1σ")
    ax.plot(numeric, sigma1_upper, color=plot_color, linewidth=1.1, alpha=0.7, linestyle=":")
    ax.plot(numeric, sigma1_lower, color=plot_color, linewidth=1.1, alpha=0.7, linestyle=":")
    ax.plot(numeric, sigma2_upper, color="#475569", linewidth=1.0, alpha=0.6, linestyle="--")
    ax.plot(numeric, sigma2_lower, color="#475569", linewidth=1.0, alpha=0.6, linestyle="--")


def collect_extrema(
    prediction_values: Sequence[float], prediction_uncertainties: Sequence[float]
) -> List[float]:
    """Collect extrema from prediction values and uncertainties."""
    extrema: List[float] = []
    for value, uncertainty in zip(prediction_values, prediction_uncertainties):
        extrema.extend([value + uncertainty, value - uncertainty])
    return extrema
