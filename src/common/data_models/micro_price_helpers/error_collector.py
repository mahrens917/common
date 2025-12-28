"""Error collection for validation reporting."""

from typing import List, Optional

from .validation_params import ValidationErrorParams

# Constants
_NUMERICAL_TOLERANCE = 1e-10


class ErrorCollector:
    """Collects validation errors for reporting."""

    @staticmethod
    def collect_spread_errors(absolute_spread: float) -> List[str]:
        """Collect errors related to spread constraints."""
        errors = []
        if absolute_spread < 0:
            errors.append(f"Spread constraint violated: absolute_spread = {absolute_spread} < 0")
        return errors

    @staticmethod
    def collect_intensity_errors(i_raw: float) -> List[str]:
        """Collect errors related to intensity constraints."""
        errors = []
        if not (0 <= i_raw <= 1):
            errors.append(f"Intensity constraint violated: I_raw = {i_raw} not in [0,1]")
        return errors

    @staticmethod
    def collect_micro_price_errors(best_bid: float, best_ask: float, p_raw: float) -> List[str]:
        """Collect errors related to micro price bounds."""
        errors = []
        if not (best_bid <= p_raw <= best_ask):
            errors.append(f"Micro price constraint violated: p_raw = {p_raw} not in [{best_bid}, {best_ask}]")
        return errors

    @staticmethod
    def collect_reconstruction_errors(
        best_bid: float,
        best_ask: float,
        p_raw: float,
        i_raw: float,
        absolute_spread: float,
    ) -> List[str]:
        """Collect errors related to bid/ask reconstruction."""
        errors = []
        reconstructed_bid = p_raw - i_raw * absolute_spread
        reconstructed_ask = p_raw + (1 - i_raw) * absolute_spread

        if abs(reconstructed_bid - best_bid) > _NUMERICAL_TOLERANCE:
            errors.append(f"Bid reconstruction constraint violated: {reconstructed_bid} != {best_bid}")
        if abs(reconstructed_ask - best_ask) > _NUMERICAL_TOLERANCE:
            errors.append(f"Ask reconstruction constraint violated: {reconstructed_ask} != {best_ask}")
        return errors

    @staticmethod
    def collect_basic_data_errors(best_bid_size: Optional[float], best_ask_size: Optional[float], option_type: str) -> List[str]:
        """Collect errors related to basic data constraints."""
        errors = []
        if best_bid_size is not None and best_bid_size < 0:
            errors.append(f"Bid size cannot be negative: {best_bid_size}")
        if best_ask_size is not None and best_ask_size < 0:
            errors.append(f"Ask size cannot be negative: {best_ask_size}")
        if option_type not in ["call", "put"]:
            errors.append(f"Option type must be 'call' or 'put': {option_type}")
        return errors

    @staticmethod
    def get_validation_errors(params: ValidationErrorParams) -> List[str]:
        """Get list of validation errors for micro price data."""
        errors = []

        try:
            errors.extend(ErrorCollector.collect_spread_errors(params.absolute_spread))
            errors.extend(ErrorCollector.collect_intensity_errors(params.i_raw))
            errors.extend(ErrorCollector.collect_micro_price_errors(params.best_bid, params.best_ask, params.p_raw))
            errors.extend(
                ErrorCollector.collect_reconstruction_errors(
                    params.best_bid,
                    params.best_ask,
                    params.p_raw,
                    params.i_raw,
                    params.absolute_spread,
                )
            )
            errors.extend(ErrorCollector.collect_basic_data_errors(params.best_bid_size, params.best_ask_size, params.option_type))
        except (  # policy_guard: allow-silent-handler
            TypeError,
            ValueError,
        ) as e:
            errors.append(f"Validation error: {str(e)}")

        return errors
