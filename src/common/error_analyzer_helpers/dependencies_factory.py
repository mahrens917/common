"""Dependency factory for ErrorAnalyzer."""

from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

from .action_suggester import ActionSuggester
from .error_categorizer import ErrorCategorizer
from .notification_sender import NotificationSender
from .recovery_reporter import RecoveryReporter
from .root_cause_identifier import RootCauseIdentifier
from .severity_evaluator import SeverityEvaluator


@dataclass
class ErrorAnalyzerDependencies:
    """Dependencies for ErrorAnalyzer."""

    categorizer: ErrorCategorizer
    severity_evaluator: SeverityEvaluator
    root_cause_identifier: RootCauseIdentifier
    action_suggester: ActionSuggester
    notification_sender: NotificationSender
    recovery_reporter: RecoveryReporter


@dataclass(frozen=True)
class OptionalDependencies:
    """Optional dependencies that can be injected."""

    categorizer: Optional[ErrorCategorizer] = None
    severity_evaluator: Optional[SeverityEvaluator] = None
    root_cause_identifier: Optional[RootCauseIdentifier] = None
    action_suggester: Optional[ActionSuggester] = None
    notification_sender: Optional[NotificationSender] = None
    recovery_reporter: Optional[RecoveryReporter] = None


T = TypeVar("T")


class ErrorAnalyzerDependenciesFactory:
    """Factory for creating ErrorAnalyzer dependencies."""

    @staticmethod
    def create(service_name: str, telegram_notifier: Optional[Callable] = None) -> ErrorAnalyzerDependencies:
        """
        Create all dependencies for ErrorAnalyzer.

        Args:
            service_name: Name of the service
            telegram_notifier: Optional telegram notifier callable

        Returns:
            ErrorAnalyzerDependencies instance
        """
        categorizer = ErrorCategorizer()
        severity_evaluator = SeverityEvaluator()
        root_cause_identifier = RootCauseIdentifier()
        action_suggester = ActionSuggester()
        notification_sender = NotificationSender(service_name, telegram_notifier)
        recovery_reporter = RecoveryReporter(service_name, telegram_notifier)

        return ErrorAnalyzerDependencies(
            categorizer=categorizer,
            severity_evaluator=severity_evaluator,
            root_cause_identifier=root_cause_identifier,
            action_suggester=action_suggester,
            notification_sender=notification_sender,
            recovery_reporter=recovery_reporter,
        )

    @staticmethod
    def create_or_use(
        service_name: str,
        telegram_notifier: Optional[Callable] = None,
        optional_deps: Optional[OptionalDependencies] = None,
    ) -> ErrorAnalyzerDependencies:
        """Create dependencies only if not all are provided."""
        if optional_deps is None:
            optional_deps = OptionalDependencies()

        provided = {
            "categorizer": optional_deps.categorizer,
            "severity_evaluator": optional_deps.severity_evaluator,
            "root_cause_identifier": optional_deps.root_cause_identifier,
            "action_suggester": optional_deps.action_suggester,
            "notification_sender": optional_deps.notification_sender,
            "recovery_reporter": optional_deps.recovery_reporter,
        }

        if all(value is not None for value in provided.values()):
            return ErrorAnalyzerDependencies(**provided)  # type: ignore[arg-type]

        deps = ErrorAnalyzerDependenciesFactory.create(service_name, telegram_notifier)

        return ErrorAnalyzerDependencies(
            categorizer=_use_default(provided["categorizer"], deps.categorizer),
            severity_evaluator=_use_default(provided["severity_evaluator"], deps.severity_evaluator),
            root_cause_identifier=_use_default(provided["root_cause_identifier"], deps.root_cause_identifier),
            action_suggester=_use_default(provided["action_suggester"], deps.action_suggester),
            notification_sender=_use_default(provided["notification_sender"], deps.notification_sender),
            recovery_reporter=_use_default(provided["recovery_reporter"], deps.recovery_reporter),
        )


def _use_default(value: Optional[T], value_on_error: T) -> T:
    """Return `value` if provided, otherwise the supplied value_on_error."""
    return value if value is not None else value_on_error
