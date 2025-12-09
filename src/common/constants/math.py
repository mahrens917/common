"""Mathematical constants and precision thresholds.

These constants define precision levels for floating-point comparisons
and numerical operations throughout the codebase.
"""

# Float comparison tolerance
FLOAT_TOLERANCE = 1e-10

# Precision thresholds
HIGH_PRECISION = 0.1
STANDARD_PRECISION = 1.0
FINE_PRECISION = 5.0

__all__ = [
    "FLOAT_TOLERANCE",
    "HIGH_PRECISION",
    "STANDARD_PRECISION",
    "FINE_PRECISION",
]
