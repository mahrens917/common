"""State management for alert suppression statistics and persistence."""

from __future__ import annotations

from typing import Any, Dict

from .suppression_tracker import SuppressionDecision, SuppressionTracker


class StateManager:
    """Manages statistics and state for alert suppression system."""

    def __init__(self, tracker: SuppressionTracker):
        """
        Initialize state manager.

        Args:
            tracker: Suppression tracker instance
        """
        self.tracker = tracker

    def get_suppression_statistics(
        self,
        enabled: bool,
        grace_period_seconds: int,
        max_suppression_duration_seconds: int,
        suppressed_alert_types: list,
    ) -> Dict[str, Any]:
        """
        Get statistics about alert suppression activity.

        Args:
            enabled: Whether suppression is enabled
            grace_period_seconds: Grace period duration
            max_suppression_duration_seconds: Max suppression duration
            suppressed_alert_types: List of suppressed alert types

        Returns:
            Dictionary with suppression statistics
        """
        if not self.tracker.has_history():
            return {
                "total_decisions": 0,
                "suppressed_count": 0,
                "suppression_rate": 0.0,
                "by_service": {},
                "by_alert_type": {},
                "rule_config": {
                    "enabled": enabled,
                    "grace_period_seconds": grace_period_seconds,
                    "max_suppression_duration_seconds": max_suppression_duration_seconds,
                    "suppressed_alert_types": suppressed_alert_types,
                },
            }

        decisions = self.tracker.get_all_decisions()
        total_decisions = len(decisions)
        suppressed_count = sum(1 for d in decisions if d.should_suppress)

        by_service = self._compute_by_service_stats(decisions)
        by_alert_type = self._compute_by_alert_type_stats(decisions)

        suppression_rate = 0.0
        if total_decisions > 0:
            suppression_rate = suppressed_count / total_decisions

        return {
            "total_decisions": total_decisions,
            "suppressed_count": suppressed_count,
            "suppression_rate": suppression_rate,
            "by_service": by_service,
            "by_alert_type": by_alert_type,
            "rule_config": {
                "enabled": enabled,
                "grace_period_seconds": grace_period_seconds,
                "max_suppression_duration_seconds": max_suppression_duration_seconds,
                "suppressed_alert_types": suppressed_alert_types,
            },
        }

    def _compute_by_service_stats(self, decisions: list[SuppressionDecision]) -> Dict[str, Dict[str, int]]:
        """Compute statistics grouped by service."""
        by_service = {}
        for decision in decisions:
            service = decision.service_name
            if service not in by_service:
                by_service[service] = {"total": 0, "suppressed": 0}
            by_service[service]["total"] += 1
            if decision.should_suppress:
                by_service[service]["suppressed"] += 1
        return by_service

    def _compute_by_alert_type_stats(self, decisions: list[SuppressionDecision]) -> Dict[str, Dict[str, int]]:
        """Compute statistics grouped by alert type."""
        by_alert_type = {}
        for decision in decisions:
            alert_type = decision.alert_type.value
            if alert_type not in by_alert_type:
                by_alert_type[alert_type] = {"total": 0, "suppressed": 0}
            by_alert_type[alert_type]["total"] += 1
            if decision.should_suppress:
                by_alert_type[alert_type]["suppressed"] += 1
        return by_alert_type
