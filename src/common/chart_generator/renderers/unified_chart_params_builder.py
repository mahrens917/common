"""Helper to build UnifiedChartParams from keyword arguments."""

from typing import Any

from .base import UnifiedChartParams


def build_unified_chart_params(**kwargs: Any) -> UnifiedChartParams:
    """Build UnifiedChartParams from keyword arguments.

    Handles the special case of value_formatter_func vs value_formatter aliasing.
    All other kwargs are passed directly to UnifiedChartParams.
    """
    # Handle value_formatter aliasing
    if "value_formatter" in kwargs and "value_formatter_func" not in kwargs:
        kwargs["value_formatter_func"] = kwargs.pop("value_formatter")
    elif "value_formatter" in kwargs:
        kwargs.pop("value_formatter")

    # Handle default values for required fields
    if "timestamps" not in kwargs:
        kwargs["timestamps"] = []
    if "values" not in kwargs:
        kwargs["values"] = []
    if "chart_title" not in kwargs:
        kwargs["chart_title"] = ""
    if "y_label" not in kwargs:
        kwargs["y_label"] = ""

    return UnifiedChartParams(**kwargs)
