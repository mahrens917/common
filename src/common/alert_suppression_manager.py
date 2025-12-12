"""Alert suppression manager for intelligent monitoring alert filtering."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .alert_suppression_manager_helpers.alert_evaluator import AlertEvaluator, SuppressionRule
from .alert_suppression_manager_helpers.config_loader import (
    build_suppression_rule_from_config,
    load_suppression_config,
)
from .alert_suppression_manager_helpers.context_builder import ContextBuilder
from .alert_suppression_manager_helpers.decision_coordinator import DecisionCoordinator
from .alert_suppression_manager_helpers.dependency_initializer import DependencyInitializer
from .alert_suppression_manager_helpers.error_classifier_adapter import ErrorClassifierAdapter
from .alert_suppression_manager_helpers.state_manager import StateManager
from .alert_suppression_manager_helpers.suppression_tracker import (
    AlertType,
    SuppressionDecision,
    SuppressionTracker,
)
from .alert_suppression_manager_helpers.time_window_manager import TimeWindowManager
from .reconnection_error_patterns import ReconnectionErrorClassifier

logger = logging.getLogger(__name__)


def _load_rule_and_mapping(suppression_rule: Optional[SuppressionRule], config_path: str) -> Tuple[SuppressionRule, Dict[str, str]]:
    if suppression_rule:
        return suppression_rule, {}
    config = load_suppression_config(config_path)
    return (
        build_suppression_rule_from_config(config),
        config["suppression_rules"]["service_type_mapping"],
    )


@dataclass
class _SuppressionComponents:
    dependency_init: DependencyInitializer
    tracker: SuppressionTracker
    evaluator: AlertEvaluator
    time_window_manager: TimeWindowManager
    context_builder: ContextBuilder
    decision_coordinator: DecisionCoordinator
    state_manager: StateManager
    error_adapter: Optional[ErrorClassifierAdapter]


def _build_components(rule: SuppressionRule) -> _SuppressionComponents:
    dependency_init = DependencyInitializer()
    tracker = SuppressionTracker(max_history_entries=1000)
    evaluator = AlertEvaluator(rule)
    time_window_manager = TimeWindowManager()
    context_builder = ContextBuilder(time_window_manager)
    decision_coordinator = DecisionCoordinator(
        suppression_rule=rule,
        tracker=tracker,
        evaluator=evaluator,
        context_builder=context_builder,
    )
    state_manager = StateManager(tracker)
    error_adapter = ErrorClassifierAdapter(ReconnectionErrorClassifier())
    return _SuppressionComponents(
        dependency_init=dependency_init,
        tracker=tracker,
        evaluator=evaluator,
        time_window_manager=time_window_manager,
        context_builder=context_builder,
        decision_coordinator=decision_coordinator,
        state_manager=state_manager,
        error_adapter=error_adapter,
    )


def _log_configuration(rule: SuppressionRule) -> None:
    logger.debug(
        "Alert suppression manager initialized (enabled: %s, grace_period: %ss, suppressed_types: %s)",
        rule.enabled,
        rule.grace_period_seconds,
        [t.value for t in rule.suppressed_alert_types],
    )


class AlertSuppressionManager:
    """Manager for intelligent alert suppression during reconnection events."""

    def __init__(
        self,
        suppression_rule: Optional[SuppressionRule] = None,
        config_path: str = "config/monitor_config.json",
    ):
        self.suppression_rule, self.service_type_mapping = _load_rule_and_mapping(suppression_rule, config_path)
        components = _build_components(self.suppression_rule)
        self.dependency_init = components.dependency_init
        self.tracker = components.tracker
        self.evaluator = components.evaluator
        self.time_window_manager = components.time_window_manager
        self.context_builder = components.context_builder
        self.decision_coordinator = components.decision_coordinator
        self.state_manager = components.state_manager
        self.error_adapter: Optional[ErrorClassifierAdapter] = components.error_adapter
        _log_configuration(self.suppression_rule)

    def _require_error_adapter(self) -> ErrorClassifierAdapter:
        if self.error_adapter is None:
            raise RuntimeError("Error adapter not initialized")
        return self.error_adapter

    async def initialize(self) -> None:
        await self.dependency_init.initialize()
        if self.dependency_init.error_classifier:
            self.error_adapter = ErrorClassifierAdapter(self.dependency_init.error_classifier)

    def _resolve_service_type(self, service_name: str) -> str:
        try:
            return self.service_type_mapping[service_name]
        except KeyError as exc:  # policy_guard: allow-silent-handler
            raise KeyError(
                f"No service type mapping configured for '{service_name}'. "
                "Update monitor_config.json.alert_suppression.suppression_rules.service_type_mapping."
            ) from exc

    async def should_suppress_alert(
        self, service_name: str, alert_type: AlertType, error_message: Optional[str] = None
    ) -> SuppressionDecision:
        await self.initialize()
        state_tracker, error_classifier = self.dependency_init.require_dependencies()
        service_type = self._resolve_service_type(service_name)
        return await self.decision_coordinator.make_decision(
            service_name=service_name,
            service_type=service_type,
            alert_type=alert_type,
            error_message=error_message,
            state_tracker=state_tracker,
            error_classifier=error_classifier,
        )

    async def get_suppression_reason(self, service_name: str, alert_type: AlertType) -> Optional[str]:
        decision = await self.should_suppress_alert(service_name, alert_type)
        return decision.reason if decision.should_suppress else None

    def classify_error_type(self, service_name: str, error_message: str) -> str:
        return self._require_error_adapter().classify_error_type(service_name, error_message)

    def is_reconnection_error(self, service_name: str, error_message: str) -> bool:
        return self._require_error_adapter().is_reconnection_error(service_name, error_message)

    def get_suppression_statistics(self) -> Dict[str, Any]:
        return self.state_manager.get_suppression_statistics(
            enabled=self.suppression_rule.enabled,
            grace_period_seconds=self.suppression_rule.grace_period_seconds,
            max_suppression_duration_seconds=self.suppression_rule.max_suppression_duration_seconds,
            suppressed_alert_types=[t.value for t in self.suppression_rule.suppressed_alert_types],
        )

    def get_recent_decisions(self, limit: int = 50) -> List[SuppressionDecision]:
        return self.tracker.get_recent_decisions(limit)


_alert_suppression_manager: Optional[AlertSuppressionManager] = None


async def get_alert_suppression_manager() -> AlertSuppressionManager:
    """Get the global alert suppression manager instance."""
    global _alert_suppression_manager
    if _alert_suppression_manager is None:
        _alert_suppression_manager = AlertSuppressionManager()
        await _alert_suppression_manager.initialize()
    return _alert_suppression_manager
