"""Validation for micro price calculations."""


class CalculationValidator:
    """Validates micro price calculation constraints."""

    @staticmethod
    def validate_absolute_spread(absolute_spread: float) -> None:
        """Validate absolute spread."""
        if absolute_spread < 0:
            raise TypeError(f"Absolute spread must be non-negative: {absolute_spread}")

    @staticmethod
    def validate_intensity(i_raw: float) -> None:
        """Validate raw intensity."""
        if not (0 <= i_raw <= 1):
            raise TypeError(f"Raw intensity (I_raw) must be in [0,1]: {i_raw}")

    @staticmethod
    def validate_raw_micro_price(p_raw: float) -> None:
        """Validate raw micro price."""
        if p_raw <= 0:
            raise TypeError(f"Raw micro price (p_raw) must be positive: {p_raw}")

    @staticmethod
    def validate_micro_price_calculations(
        absolute_spread: float,
        i_raw: float,
        p_raw: float,
    ) -> None:
        """Validate micro price calculation constraints."""
        CalculationValidator.validate_absolute_spread(absolute_spread)
        CalculationValidator.validate_intensity(i_raw)
        CalculationValidator.validate_raw_micro_price(p_raw)
