from __future__ import annotations

"""Dependency factory for AlertSuppressionManager."""

from dataclasses import dataclass, fields
from typing import Optional

from .alert_evaluator import AlertEvaluator, SuppressionRule
from .context_builder import ContextBuilder
from .decision_coordinator import DecisionCoordinator
from .dependency_initializer import DependencyInitializer
from .error_classifier_adapter import ErrorClassifierAdapter
from .state_manager import StateManager
from .suppression_tracker import SuppressionTracker
from .time_window_manager import TimeWindowManager


@dataclass
class AlertSuppressionManagerDependencies:
    """Container for all AlertSuppressionManager dependencies."""  # gitleaks:allow

    dependency_init: DependencyInitializer
    tracker: SuppressionTracker
    evaluator: AlertEvaluator
    time_window_manager: TimeWindowManager
    context_builder: ContextBuilder
    decision_coordinator: DecisionCoordinator
    state_manager: StateManager
    error_adapter: Optional[ErrorClassifierAdapter]


@dataclass(frozen=True)
class OptionalDependencies:
    """Optional dependencies that can be injected."""

    dependency_init: DependencyInitializer | None = None
    tracker: SuppressionTracker | None = None
    evaluator: AlertEvaluator | None = None
    time_window_manager: TimeWindowManager | None = None
    context_builder: ContextBuilder | None = None
    decision_coordinator: DecisionCoordinator | None = None
    state_manager: StateManager | None = None
    error_adapter: ErrorClassifierAdapter | None = None


class AlertSuppressionManagerDependenciesFactory:  # gitleaks:allow
    """Factory for creating AlertSuppressionManager dependencies."""

    @staticmethod
    def create(
        suppression_rule: SuppressionRule,
    ) -> AlertSuppressionManagerDependencies:  # gitleaks:allow
        """Create all dependencies for AlertSuppressionManager."""
        dependency_init = DependencyInitializer()
        tracker = SuppressionTracker(max_history_entries=1000)
        evaluator = AlertEvaluator(suppression_rule)
        time_window_manager = TimeWindowManager()
        context_builder = ContextBuilder(time_window_manager)
        decision_coordinator = DecisionCoordinator(
            suppression_rule=suppression_rule,
            tracker=tracker,
            evaluator=evaluator,
            context_builder=context_builder,
        )
        state_manager = StateManager(tracker)

        return AlertSuppressionManagerDependencies(  # gitleaks:allow
            dependency_init=dependency_init,
            tracker=tracker,
            evaluator=evaluator,
            time_window_manager=time_window_manager,
            context_builder=context_builder,
            decision_coordinator=decision_coordinator,
            state_manager=state_manager,
            error_adapter=None,
        )

    @staticmethod
    def create_or_use(
        suppression_rule: SuppressionRule,
        optional_deps: OptionalDependencies | None = None,
    ) -> AlertSuppressionManagerDependencies:  # gitleaks:allow
        """Create dependencies only if not all are provided."""
        if optional_deps is None:
            return AlertSuppressionManagerDependenciesFactory.create(suppression_rule)

        if all(getattr(optional_deps, field.name) for field in fields(OptionalDependencies)):
            return AlertSuppressionManagerDependencies(**vars(optional_deps))  # gitleaks:allow

        defaults = AlertSuppressionManagerDependenciesFactory.create(suppression_rule)
        merged = {
            field.name: getattr(optional_deps, field.name) or getattr(defaults, field.name)
            for field in fields(AlertSuppressionManagerDependencies)
        }
        return AlertSuppressionManagerDependencies(**merged)  # gitleaks:allow
