"""Tests for re-exported time utilities."""

import math

from src.common import time_utils as time_utils_module


def test_time_utils_exports_constants():
    assert hasattr(time_utils_module, "DERIBIT_EXPIRY_HOUR")
    assert hasattr(time_utils_module, "EPOCH_START")
    assert hasattr(time_utils_module, "math")


def test_time_utils_exports_functions():
    assert time_utils_module.parse_timestamp("2025-01-01T00:00:00Z")
    assert time_utils_module.format_time_key(0)
    assert time_utils_module.get_timezone_from_coordinates(0.0, 0.0)
