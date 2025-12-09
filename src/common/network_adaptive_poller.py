"""
Network-adaptive polling manager for services with variable network conditions.

Automatically adjusts polling intervals based on actual network performance,
optimizing for both fast (AWS) and slow (residential) network environments.
"""

import logging
import time
from dataclasses import dataclass
from typing import List, Optional

from .network_adaptive_poller_helpers.interval_adjuster import IntervalAdjuster
from .network_adaptive_poller_helpers.network_classifier import NetworkClassifier

logger = logging.getLogger(__name__)


# Constants
_CONST_3 = 3


@dataclass
class NetworkMetrics:
    """Network performance metrics for adaptive polling."""

    request_time: float
    success: bool
    timestamp: float


class NetworkAdaptivePoller:
    """
    Adaptive polling manager that adjusts intervals based on network performance.

    Tracks request times and success rates to automatically optimize polling
    frequency for the current network environment. Fast networks (AWS) get
    shorter intervals, slow networks (residential) get longer intervals.
    """

    def __init__(
        self,
        base_interval_seconds: int = 30,
        min_interval_seconds: int = 20,
        max_interval_seconds: int = 180,
        metrics_window_size: int = 10,
    ):
        """
        Initialize network-adaptive poller.

        Args:
            base_interval_seconds: Starting polling interval
            min_interval_seconds: Minimum allowed interval (fast networks)
            max_interval_seconds: Maximum allowed interval (slow networks)
            metrics_window_size: Number of recent requests to track
        """
        self.base_interval_seconds = base_interval_seconds
        self.min_interval_seconds = min_interval_seconds
        self.max_interval_seconds = max_interval_seconds
        self.metrics_window_size = metrics_window_size

        # Current state
        self.current_interval_seconds = base_interval_seconds
        self.recent_metrics: List[NetworkMetrics] = []

        logger.info(
            f"Network adaptive poller initialized: "
            f"base={base_interval_seconds}s, "
            f"range=[{min_interval_seconds}s-{max_interval_seconds}s]"
        )

    def record_request(self, request_time: float, success: bool) -> None:
        """
        Record a network request result for adaptive polling.

        Args:
            request_time: Time taken for the request in seconds
            success: Whether the request succeeded
        """
        metric = NetworkMetrics(request_time=request_time, success=success, timestamp=time.time())

        self.recent_metrics.append(metric)

        # Keep only recent metrics within window
        if len(self.recent_metrics) > self.metrics_window_size:
            self.recent_metrics.pop(0)

        # Update interval based on performance
        self.current_interval_seconds = IntervalAdjuster.calculate_adjusted_interval(
            self.recent_metrics,
            self.current_interval_seconds,
            self.min_interval_seconds,
            self.max_interval_seconds,
        )

    def get_current_interval(self) -> int:
        """Get the current polling interval in seconds."""
        return self.current_interval_seconds

    def get_network_summary(self) -> Optional[dict]:
        """
        Get summary of recent network performance.

        Returns:
            Dictionary with performance metrics or None if insufficient data
        """
        if len(self.recent_metrics) < _CONST_3:
            return None

        avg_time = sum(m.request_time for m in self.recent_metrics) / len(self.recent_metrics)
        success_rate = sum(1 for m in self.recent_metrics if m.success) / len(self.recent_metrics)

        return {
            "current_interval_seconds": self.current_interval_seconds,
            "avg_request_time_seconds": round(avg_time, 2),
            "success_rate": round(success_rate, _CONST_3),
            "sample_size": len(self.recent_metrics),
            "network_type": NetworkClassifier.classify_network_type(avg_time, success_rate),
        }

    def _classify_network_type(self, avg_time: float, success_rate: float) -> str:
        """Classify network type based on timing and success metrics."""
        return NetworkClassifier.classify_network_type(avg_time, success_rate)
