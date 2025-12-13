"""Result generation for daily maximum temperatures."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from common.exceptions import DataError
from src.weather.temperature_converter import cli_temp_f

from .confidence_calculator import ConfidenceCalculator

logger = logging.getLogger(__name__)


@dataclass
class DailyMaxResult:
    """Result of daily maximum temperature calculation."""

    max_temp_f: int  # Temperature in Fahrenheit for trading decisions
    confidence: str  # "HIGH" or "MEDIUM"
    precision_c: float  # Source precision in Celsius (0.1 or 1.0)
    source: str  # 'hourly' or '6h'
    timestamp: Optional[datetime] = None  # When this max was observed


class ResultGenerator:
    """Generates results and adjusted temperatures for trading rules."""

    @staticmethod
    def get_daily_max_result(state: Dict[str, Any]) -> Optional[DailyMaxResult]:
        max_temp_c = state.get("max_temp_c")
        if not isinstance(max_temp_c, (int, float)):
            logger.error("Daily max result requested but invalid max_temp_c=%s", max_temp_c)
            return None
        if max_temp_c == float("-inf"):
            return None

        precision = state.get("precision")
        source = state.get("source")

        if precision is None or source is None:
            logger.error("Daily max result requested but precision=%s, source=%s", precision, source)
            return None

        # Convert to Fahrenheit using CLI formula
        max_temp_f = cli_temp_f(max_temp_c)
        confidence = ConfidenceCalculator.get_confidence_level(precision)

        logger.debug(f"Daily max result: {max_temp_f}°F from {max_temp_c}°C " f"({confidence} confidence, {source} source)")

        return DailyMaxResult(
            max_temp_f=max_temp_f,
            confidence=confidence,
            precision_c=precision,
            source=source,
            timestamp=state.get("timestamp"),
        )

    @staticmethod
    def get_adjusted_temp_for_rule(state: Dict[str, Any], rule_type: str) -> int:
        max_temp_c = state.get("max_temp_c")
        if not isinstance(max_temp_c, (int, float)):
            raise DataError("No temperature data available")
        if max_temp_c == float("-inf"):
            raise DataError("No temperature data available")

        precision = state.get("precision")
        margin_c = ConfidenceCalculator.get_safety_margin_c(precision)

        if rule_type == "conservative":
            # Add margin for conservative triggers (Rules 3, 5)
            adjusted_c = max_temp_c + margin_c
        elif rule_type == "aggressive":
            # Subtract margin for aggressive triggers (Rules 4, 6)
            adjusted_c = max_temp_c - margin_c
        else:
            raise ValueError(f"Unknown rule_type: {rule_type}")

        return cli_temp_f(adjusted_c)

    @staticmethod
    def get_hourly_only_max_f(state: Dict[str, Any]) -> Optional[int]:
        hourly_max_temp_c = state.get("hourly_max_temp_c")
        if not isinstance(hourly_max_temp_c, (int, float)):
            return None
        if hourly_max_temp_c == float("-inf"):
            return None

        # Use CLI conversion formula
        return cli_temp_f(hourly_max_temp_c)
