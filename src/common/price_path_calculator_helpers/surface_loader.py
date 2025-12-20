"""Load and validate GP surfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from src.pdf.phases.phase_5_gp_interpolation import MicroPriceGPSurface


class PricePathComputationError(Exception):
    """Raised when price path computation fails."""


class SurfaceLoader:
    """Load and validate GP surfaces from storage."""

    def load_surface(
        self,
        currency: str,
        loader_fn: Callable[[str], Optional[Any]],
        ensure_metrics_fn: Callable[[Any, str], None],
    ) -> Any:
        """Load surface and ensure path metrics are available."""
        surface = loader_fn(currency)
        if surface is None:
            raise PricePathComputationError(f"No GP surface available for {currency.upper()}")
        if not surface.is_fitted:
            raise PricePathComputationError(f"GP surface for {currency.upper()} is not fitted")

        ensure_metrics_fn(surface, currency)
        return surface
