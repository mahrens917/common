"""Core logic for evaluating whether alerts should be suppressed."""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Set

from .suppression_tracker import AlertType, SuppressionDecision

logger = logging.getLogger(__name__)


DEFAULT_MAX_SUPPRESSION_DURATION_SECONDS = 1800


@dataclass
class SuppressionRule:
    """
    Configuration for alert suppression rules.

    Defines which alert types should be suppressed under what conditions,
    with configurable grace periods and error pattern matching.
    """

    enabled: bool = True
    grace_period_seconds: int = 300  # 5 minutes default
    suppressed_alert_types: Set[AlertType] = field(
        default_factory=lambda: {
            AlertType.ERROR_LOG,
            AlertType.STALE_LOG,
            AlertType.MESSAGE_METRICS,
        }
    )
    require_reconnection_error_pattern: bool = True
    max_suppression_duration_seconds: int = DEFAULT_MAX_SUPPRESSION_DURATION_SECONDS  # 30 minutes max


@dataclass(frozen=True)
class SuppressionContext:
    """Complete context for suppression evaluation."""

    service_type: str
    is_in_reconnection: bool
    is_in_grace_period: bool
    reconnection_duration: Optional[float]
    grace_period_remaining_seconds: Optional[float]
    is_reconnection_error: bool


class AlertEvaluator:
    """Evaluates whether alerts should be suppressed based on context."""

    def __init__(self, suppression_rule: SuppressionRule):
        self.suppression_rule = suppression_rule

    def is_alert_type_supported(self, alert_type: AlertType) -> bool:
        return alert_type in self.suppression_rule.suppressed_alert_types

    def build_decision(
        self,
        service_name: str,
        alert_type: AlertType,
        context: SuppressionContext,
        error_message: Optional[str],
    ) -> SuppressionDecision:
        should_suppress = False
        reason_parts: List[str] = []

        if context.is_reconnection_error and error_message:
            should_suppress = True
            reason_parts.append("error matches reconnection pattern")
            _log_reconnection_error(service_name, error_message)
        elif alert_type == AlertType.RECOVERY:
            should_suppress, reason_parts = _evaluate_recovery_alert(context)
        elif context.is_in_reconnection:
            should_suppress, reason_parts = _evaluate_during_reconnection(self.suppression_rule, context)
        elif context.is_in_grace_period:
            should_suppress = True
            reason_parts.append("service is in post-reconnection grace period")

        reason = "; ".join(reason_parts) if reason_parts else "no suppression conditions met"
        return SuppressionDecision(
            should_suppress=should_suppress,
            reason=reason,
            service_name=service_name,
            alert_type=alert_type,
            suppression_duration_seconds=context.reconnection_duration,
            grace_period_remaining_seconds=context.grace_period_remaining_seconds,
        )


def _log_reconnection_error(service_name: str, error_message: Optional[str]) -> None:
    if error_message:
        logger.debug("Suppressing reconnection error for %s: %s", service_name, error_message[:100])


def _evaluate_recovery_alert(context: SuppressionContext) -> tuple[bool, List[str]]:
    reason_parts: List[str] = []
    if context.is_in_reconnection or context.is_in_grace_period:
        phase = "reconnection mode" if context.is_in_reconnection else "post-reconnection grace period"
        reason_parts.append(f"service is in {phase}")
        reason_parts.append("recovery notification suppressed to avoid redundancy")
        return True, reason_parts
    return False, reason_parts


def _evaluate_during_reconnection(rule: SuppressionRule, context: SuppressionContext) -> tuple[bool, List[str]]:
    reason_parts: List[str] = []
    max_duration = rule.max_suppression_duration_seconds
    if context.reconnection_duration and context.reconnection_duration > max_duration:
        reason_parts.append(f"reconnection duration ({context.reconnection_duration:.1f}s) exceeds max suppression time")
        return False, reason_parts
    reason_parts.append("service is in reconnection mode")
    if context.reconnection_duration is not None:
        reason_parts.append(f"duration: {context.reconnection_duration:.1f}s")
    return True, reason_parts
