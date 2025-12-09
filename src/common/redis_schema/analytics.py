from __future__ import annotations

"""Keys for analytics outputs (PDF, probabilities, etc.)."""


from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.common.exceptions import ValidationError

from .namespaces import KeyBuilder, RedisNamespace, sanitize_segment
from .validators import register_namespace

register_namespace("analytics:pdf:", "PDF pipeline surfaces and diagnostics")
register_namespace("analytics:probability:", "Human-readable probability slices")


class SurfaceType(str, Enum):
    """Known surface families produced by the PDF pipeline."""

    BID = "bid"
    ASK = "ask"
    SPREAD = "spread"
    INTENSITY = "intensity"
    MICRO_PRICE = "micro_price"


@dataclass(frozen=True)
class PdfSurfaceKey:
    """Redis key for storing a single surface evaluation."""

    currency: str
    surface_type: SurfaceType
    expiry_iso: str
    strike: str
    grid_point: Optional[str] = None

    def key(self) -> str:
        try:
            expiry_segment = sanitize_segment(self.expiry_iso)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        segments = [
            "pdf",
            sanitize_segment(self.currency),
            "surface",
            self.surface_type.value,
            expiry_segment,
            sanitize_segment(self.strike),
        ]
        if self.grid_point:
            segments.append(sanitize_segment(self.grid_point))
        builder = KeyBuilder(RedisNamespace.ANALYTICS, tuple(segments))
        return builder.render()


@dataclass(frozen=True)
class ProbabilitySliceKey:
    """Key for aggregated probability outputs (e.g., buckets, ranges)."""

    currency: str
    expiry_iso: str
    slice_name: str

    def key(self) -> str:
        try:
            slice_segment = sanitize_segment(self.slice_name)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc
        segments = [
            "probability",
            sanitize_segment(self.currency),
            sanitize_segment(self.expiry_iso),
            slice_segment,
        ]
        builder = KeyBuilder(RedisNamespace.ANALYTICS, tuple(segments))
        return builder.render()
