"""Parameter dataclasses for prediction overlay rendering."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence


@dataclass(frozen=True)
class PredictionOverlayParameters:
    """Parameters for rendering prediction overlays on charts."""

    ax: object
    historical_timestamps: Sequence[datetime]
    historical_values: Sequence[float]
    prediction_timestamps: Optional[Sequence[datetime]]
    prediction_values: Optional[Sequence[float]]
    prediction_uncertainties: Optional[Sequence[float]]
    plot_color: str


@dataclass(frozen=True)
class ConditionalOverlayParameters:
    """Parameters for conditionally rendering prediction overlays."""

    ax: object
    historical_naive: Sequence[datetime]
    historical_values: Sequence[float]
    precomputed_prediction: Optional[Sequence[datetime]]
    prediction_timestamps: Optional[Sequence[datetime]]
    prediction_values: Optional[Sequence[float]]
    prediction_uncertainties: Optional[Sequence[float]]
    plot_color: str


@dataclass(frozen=True)
class EnvelopeRenderParameters:
    """Parameters for rendering uncertainty envelopes."""

    ax: object
    anchor_numeric: Optional[float]
    prediction_numeric: object  # np.ndarray
    merged_numeric: object  # np.ndarray
    merged_values: object  # np.ndarray
    prediction_values: Sequence[float]
    prediction_uncertainties: Sequence[float]
    plot_color: str


@dataclass(frozen=True)
class EnvelopeBandParameters:
    """Parameters for drawing envelope bands."""

    ax: object
    numeric: object  # np.ndarray
    values: object  # np.ndarray
    sigma: object  # np.ndarray
    colors: tuple
    plot_color: str
