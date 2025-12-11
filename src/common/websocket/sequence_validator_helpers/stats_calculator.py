"""Statistics calculation and logging"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class StatsCalculator:
    """Calculates and logs sequence validation statistics"""

    def __init__(self, service_name: str, max_gap_tolerance: int, tracking_state):
        """
        Initialize stats calculator

        Args:
            service_name: Name of the service for logging
            max_gap_tolerance: Maximum gap tolerance value
            tracking_state: TrackingState instance
        """
        self.service_name = service_name
        self.max_gap_tolerance = max_gap_tolerance
        self.tracking_state = tracking_state

    def get_stats(self) -> Dict[str, Any]:
        """
        Get sequence validation statistics

        Returns:
            Dictionary with validation statistics
        """
        total_sids = len(self.tracking_state.sid_to_last_seq)
        total_gaps = sum(self.tracking_state.sid_to_gap_count.values())

        stats = {
            "service_name": self.service_name,
            "total_sids": total_sids,
            "total_gaps": total_gaps,
            "max_gap_tolerance": self.max_gap_tolerance,
            "sids_with_gaps": len([count for count in self.tracking_state.sid_to_gap_count.values() if count > 0]),
        }

        if total_sids > 0:
            stats["avg_gaps_per_sid"] = total_gaps / total_sids
            if self.tracking_state.sid_to_gap_count:
                stats["max_gaps_for_sid"] = max(self.tracking_state.sid_to_gap_count.values())
            else:
                stats["max_gaps_for_sid"] = 0

        return stats

    def log_stats(self) -> None:
        """Log current sequence validation statistics"""
        stats = self.get_stats()

        if stats["total_sids"] == 0:
            logger.debug(f"{self.service_name} sequence validator: No active SIDs")
            return

        if "avg_gaps_per_sid" in stats:
            avg_gaps_display = f"{stats['avg_gaps_per_sid']:.1f}"
        else:
            avg_gaps_display = "0.0"
        if "max_gaps_for_sid" in stats:
            max_gaps_display = str(stats["max_gaps_for_sid"])
        else:
            max_gaps_display = "0"
        logger.info(
            f"{self.service_name} sequence stats: "
            f"SIDs={stats['total_sids']}, "
            f"total_gaps={stats['total_gaps']}, "
            f"SIDs_with_gaps={stats['sids_with_gaps']}, "
            f"avg_gaps={avg_gaps_display}, "
            f"max_gaps={max_gaps_display}"
        )
