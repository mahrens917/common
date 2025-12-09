"""Coordinates the suppression decision-making process."""

import logging
from typing import Optional

from ..connection_state_tracker import ConnectionStateTracker
from ..reconnection_error_patterns import ReconnectionErrorClassifier
from .alert_evaluator import AlertEvaluator, SuppressionRule
from .context_builder import ContextBuilder
from .suppression_tracker import AlertType, SuppressionDecision, SuppressionTracker

logger = logging.getLogger(__name__)


class DecisionCoordinator:
    """Coordinates the alert suppression decision process."""

    def __init__(
        self,
        suppression_rule: SuppressionRule,
        tracker: SuppressionTracker,
        evaluator: AlertEvaluator,
        context_builder: ContextBuilder,
    ):
        """
        Initialize decision coordinator.

        Args:
            suppression_rule: Suppression rule configuration
            tracker: Suppression tracker instance
            evaluator: Alert evaluator instance
            context_builder: Context builder instance
        """
        self.suppression_rule = suppression_rule
        self.tracker = tracker
        self.evaluator = evaluator
        self.context_builder = context_builder

    async def make_decision(
        self,
        *,
        service_name: str,
        service_type: str,
        alert_type: AlertType,
        error_message: Optional[str],
        state_tracker: ConnectionStateTracker,
        error_classifier: ReconnectionErrorClassifier,
    ) -> SuppressionDecision:
        """
        Make suppression decision for an alert.

        Args:
            service_name: Name of the service
            service_type: Type of service
            alert_type: Type of alert
            error_message: Optional error message
            state_tracker: Connection state tracker
            error_classifier: Error classifier

        Returns:
            SuppressionDecision
        """
        if not self.suppression_rule.enabled:
            decision = SuppressionDecision(
                should_suppress=False,
                reason="Alert suppression is disabled",
                service_name=service_name,
                alert_type=alert_type,
            )
            self.tracker.record_decision(decision)
            return decision

        if not self.evaluator.is_alert_type_supported(alert_type):
            decision = SuppressionDecision(
                should_suppress=False,
                reason=f"Alert type {alert_type.value} not configured for suppression",
                service_name=service_name,
                alert_type=alert_type,
            )
            self.tracker.record_decision(decision)
            return decision

        context = await self.context_builder.build_context(
            service_name=service_name,
            service_type=service_type,
            grace_period_seconds=self.suppression_rule.grace_period_seconds,
            error_message=error_message,
            state_tracker=state_tracker,
            error_classifier=error_classifier,
            require_reconnection_error_pattern=self.suppression_rule.require_reconnection_error_pattern,
        )

        decision = self.evaluator.build_decision(
            service_name=service_name,
            alert_type=alert_type,
            context=context,
            error_message=error_message,
        )

        self.tracker.record_decision(decision)

        if decision.should_suppress:
            logger.debug(
                f"Suppressing {alert_type.value} alert for {service_name}: {decision.reason}"
            )

        return decision
