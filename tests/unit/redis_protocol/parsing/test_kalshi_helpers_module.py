"""Tests for kalshi_helpers.py module-level exports."""

# Import the specific .py file by using sys.path manipulation
import importlib.util
import sys
from pathlib import Path


def test_kalshi_helpers_py_module_all():
    """Test that the kalshi_helpers.py __all__ export list is correct."""
    # Load the kalshi_helpers.py file directly
    module_path = Path("/Users/mahrens917/common/src/common/redis_protocol/parsing/kalshi_helpers.py")
    spec = importlib.util.spec_from_file_location("kalshi_helpers_py", module_path)
    assert spec is not None
    assert spec.loader is not None
    kalshi_helpers_module = importlib.util.module_from_spec(spec)
    sys.modules["kalshi_helpers_py"] = kalshi_helpers_module
    spec.loader.exec_module(kalshi_helpers_module)

    assert hasattr(kalshi_helpers_module, "__all__")
    expected = [
        "parse_year_month_day_format",
        "parse_intraday_format",
        "parse_day_month_year_format",
    ]
    assert kalshi_helpers_module.__all__ == expected


def test_kalshi_helpers_py_module_exports_functions():
    """Test that kalshi_helpers.py exports all expected functions."""
    # Load the kalshi_helpers.py file directly
    module_path = Path("/Users/mahrens917/common/src/common/redis_protocol/parsing/kalshi_helpers.py")
    spec = importlib.util.spec_from_file_location("kalshi_helpers_py2", module_path)
    assert spec is not None
    assert spec.loader is not None
    kalshi_helpers_module = importlib.util.module_from_spec(spec)
    sys.modules["kalshi_helpers_py2"] = kalshi_helpers_module
    spec.loader.exec_module(kalshi_helpers_module)

    assert hasattr(kalshi_helpers_module, "parse_year_month_day_format")
    assert hasattr(kalshi_helpers_module, "parse_intraday_format")
    assert hasattr(kalshi_helpers_module, "parse_day_month_year_format")
    assert callable(kalshi_helpers_module.parse_year_month_day_format)
    assert callable(kalshi_helpers_module.parse_intraday_format)
    assert callable(kalshi_helpers_module.parse_day_month_year_format)
