from __future__ import annotations

"""Helper for calculating series statistics"""


import logging
from typing import List

from src.common.chart_generator.contexts import ChartStatistics
from src.common.chart_generator.exceptions import InsufficientDataError

logger = logging.getLogger("src.monitor.chart_generator")


class SeriesStatisticsCalculator:
    """Calculates statistical measures for chart series"""

    def compute_series_statistics(self, values: List[float], np) -> ChartStatistics:
        """Compute min, max, and mean statistics"""
        try:
            min_value = float(np.min(values))
            max_value = float(np.max(values))
            mean_value = float(np.mean(values))
        except ValueError as exc:
            raise InsufficientDataError("Cannot compute statistics without values") from exc
        return ChartStatistics(min_value=min_value, max_value=max_value, mean_value=mean_value)
