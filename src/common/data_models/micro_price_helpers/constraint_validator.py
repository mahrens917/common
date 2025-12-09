"""Validation for micro price mathematical constraints."""

# Constants
_NUMERICAL_TOLERANCE = 1e-10


class ConstraintValidator:
    """Validates that micro price calculations satisfy mathematical constraints."""

    @staticmethod
    def validate_spread_constraint(absolute_spread: float) -> None:
        """Validate that spread is non-negative."""
        if absolute_spread < 0:
            raise ValueError(f"Spread constraint violated: absolute_spread = {absolute_spread} < 0")

    @staticmethod
    def validate_intensity_constraint(i_raw: float) -> None:
        """Validate that intensity is in [0,1]."""
        if not (0 <= i_raw <= 1):
            raise ValueError(f"Intensity constraint violated: I_raw = {i_raw} not in [0,1]")

    @staticmethod
    def validate_micro_price_bounds(best_bid: float, best_ask: float, p_raw: float) -> None:
        """Validate that micro price is between bid and ask."""
        if not (best_bid <= p_raw <= best_ask):
            raise ValueError(
                f"Micro price constraint violated: p_raw = {p_raw} not in [{best_bid}, {best_ask}]"
            )

    @staticmethod
    def validate_bid_reconstruction(
        best_bid: float, p_raw: float, i_raw: float, absolute_spread: float
    ) -> None:
        """Validate bid reconstruction from micro price."""
        reconstructed_bid = p_raw - i_raw * absolute_spread
        if abs(reconstructed_bid - best_bid) > _NUMERICAL_TOLERANCE:
            raise ValueError(
                f"Bid reconstruction constraint violated: {reconstructed_bid} != {best_bid}"
            )

    @staticmethod
    def validate_ask_reconstruction(
        best_ask: float, p_raw: float, i_raw: float, absolute_spread: float
    ) -> None:
        """Validate ask reconstruction from micro price."""
        reconstructed_ask = p_raw + (1 - i_raw) * absolute_spread
        if abs(reconstructed_ask - best_ask) > _NUMERICAL_TOLERANCE:
            raise ValueError(
                f"Ask reconstruction constraint violated: {reconstructed_ask} != {best_ask}"
            )

    @staticmethod
    def validate_micro_price_constraints(
        best_bid: float,
        best_ask: float,
        absolute_spread: float,
        i_raw: float,
        p_raw: float,
    ) -> bool:
        """Validate that micro price calculations satisfy mathematical constraints."""
        ConstraintValidator.validate_spread_constraint(absolute_spread)
        ConstraintValidator.validate_intensity_constraint(i_raw)
        ConstraintValidator.validate_micro_price_bounds(best_bid, best_ask, p_raw)
        ConstraintValidator.validate_bid_reconstruction(best_bid, p_raw, i_raw, absolute_spread)
        ConstraintValidator.validate_ask_reconstruction(best_ask, p_raw, i_raw, absolute_spread)
        return True
