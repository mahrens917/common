"""Validation for mathematical relationships between micro price variables."""

import math

# Constants
_NUMERICAL_TOLERANCE = 1e-10


class RelationshipValidator:
    """Validates mathematical relationships between variables."""

    NUMERICAL_TOLERANCE = 0.01

    @staticmethod
    def validate_spread_relationship(best_bid: float, best_ask: float, absolute_spread: float) -> None:
        """Validate absolute spread equals best_ask - best_bid."""
        expected_abs_spread = best_ask - best_bid
        if abs(absolute_spread - expected_abs_spread) > _NUMERICAL_TOLERANCE:
            raise ValueError(f"Absolute spread ({absolute_spread}) must equal best_ask - best_bid ({expected_abs_spread})")

    @staticmethod
    def validate_relative_spread(absolute_spread: float, relative_spread: float, p_raw: float) -> None:
        """Validate relative spread equals absolute_spread / p_raw."""
        expected_rel_spread = absolute_spread / p_raw
        if abs(relative_spread - expected_rel_spread) > _NUMERICAL_TOLERANCE:
            raise ValueError(f"Relative spread ({relative_spread}) must equal absolute_spread / p_raw ({expected_rel_spread})")

    @staticmethod
    def validate_intensity_calculation(best_bid_size: float, best_ask_size: float, i_raw: float) -> None:
        """Validate intensity calculation from volumes."""
        total_volume = best_bid_size + best_ask_size
        if total_volume > 0:
            expected_i_raw = best_bid_size / total_volume
            if abs(i_raw - expected_i_raw) > _NUMERICAL_TOLERANCE:
                raise ValueError(f"I_raw ({i_raw}) must equal best_bid_size / (best_bid_size + best_ask_size) ({expected_i_raw})")

    @staticmethod
    def validate_micro_price_calculation(
        best_bid: float,
        best_ask: float,
        best_bid_size: float,
        best_ask_size: float,
        p_raw: float,
    ) -> None:
        """Validate volume-weighted micro price calculation."""
        total_volume = best_bid_size + best_ask_size
        if total_volume > 0:
            expected_p_raw = (best_bid * best_ask_size + best_ask * best_bid_size) / total_volume
            if abs(p_raw - expected_p_raw) > _NUMERICAL_TOLERANCE:
                raise ValueError(f"p_raw ({p_raw}) must equal volume-weighted micro price ({expected_p_raw})")

    @staticmethod
    def validate_g_transformation(absolute_spread: float, g: float) -> None:
        """Validate g = log(absolute_spread)."""
        if absolute_spread > 0:
            expected_g = math.log(absolute_spread)
            relative_error = abs(g - expected_g) / max(abs(expected_g), 1e-12)
            if relative_error > RelationshipValidator.NUMERICAL_TOLERANCE:
                raise ValueError(
                    f"g ({g}) must equal log(absolute_spread) ({expected_g}) within tolerance {RelationshipValidator.NUMERICAL_TOLERANCE}, got relative error {relative_error}"
                )

    @staticmethod
    def validate_h_transformation(i_raw: float, h: float) -> None:
        """Validate h = log(i_raw / (1 - i_raw))."""
        if 0 < i_raw < 1:
            expected_h = math.log(i_raw / (1 - i_raw))
            relative_error = abs(h - expected_h) / max(abs(expected_h), 1e-12)
            if relative_error > RelationshipValidator.NUMERICAL_TOLERANCE:
                raise ValueError(
                    f"h ({h}) must equal log(I_raw / (1 - I_raw)) ({expected_h}) within tolerance {RelationshipValidator.NUMERICAL_TOLERANCE}, got relative error {relative_error}"
                )
