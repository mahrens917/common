"""Surface validation utilities."""


class PricePathComputationError(Exception):
    """Raised when price path computation fails."""


def ensure_path_metrics(surface, currency: str) -> None:
    """Ensure surface has valid path metrics method."""
    from collections.abc import Callable as CallableType

    ensure_metrics = getattr(surface, "ensure_path_metrics", None)
    if ensure_metrics and not isinstance(ensure_metrics, CallableType):
        raise PricePathComputationError(
            f"GP surface for {currency.upper()} has non-callable ensure_path_metrics"
        )
    if ensure_metrics and isinstance(ensure_metrics, CallableType):
        try:
            ensure_metrics()
        except (RuntimeError, ValueError, TypeError) as e:
            raise PricePathComputationError(
                f"Failed to generate metrics for {currency.upper()}"
            ) from e
