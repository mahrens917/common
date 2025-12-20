"""Confidence level and safety margin calculations."""

from __future__ import annotations

# Constants
_PRECISION_HIGH = 0.1


class ConfidenceCalculator:
    """Calculates confidence levels and safety margins based on precision."""

    @staticmethod
    def get_confidence_level(precision: float | None) -> str:
        """
        Determine trading confidence from precision.

        Args:
            precision: Data precision (_PRECISION_HIGH or 1.0)

        Returns:
            "HIGH" for 0.1°C precision, "MEDIUM" for 1.0°C precision

        Raises:
            ValueError: If precision is unknown (fail-fast, no implicit defaults)
        """
        if precision == _PRECISION_HIGH:
            return "HIGH"
        elif precision == 1.0:
            return "MEDIUM"
        else:
            raise ValueError(f"Unknown precision {precision} - cannot determine confidence")

    @staticmethod
    def get_safety_margin_c(precision: float | None) -> float:
        """
        Return safety margin in Celsius based on precision.

        Args:
            precision: Data precision (_PRECISION_HIGH or 1.0)

        Returns:
            0.0°C for HIGH confidence, 0.5°C for MEDIUM confidence

        Raises:
            ValueError: If confidence cannot be determined
        """
        confidence = ConfidenceCalculator.get_confidence_level(precision)
        if confidence == "HIGH":
            return 0.0  # No margin needed for precise data
        elif confidence == "MEDIUM":
            return 0.5  # Half the uncertainty range
        else:
            raise ValueError(f"Unknown confidence level: {confidence}")
