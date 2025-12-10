"""Tests for the ErrorAnalyzer dependency factory."""

from unittest.mock import MagicMock

from common.error_analyzer_helpers import dependencies_factory
from common.error_analyzer_helpers.dependencies_factory import (
    ErrorAnalyzerDependencies,
    ErrorAnalyzerDependenciesFactory,
    OptionalDependencies,
)


def _simple_component(name):
    class Component:
        def __init__(self, *_, **__):
            self.name = name

    return Component


def test_create_forms_all_components(monkeypatch):
    """The factory should produce instances for every dependency."""
    names = {
        "ErrorCategorizer": _simple_component("categorizer"),
        "SeverityEvaluator": _simple_component("severity"),
        "RootCauseIdentifier": _simple_component("root"),
        "ActionSuggester": _simple_component("action"),
        "NotificationSender": _simple_component("notification"),
        "RecoveryReporter": _simple_component("recovery"),
    }

    for attr, implementation in names.items():
        monkeypatch.setattr(dependencies_factory, attr, implementation)

    deps = ErrorAnalyzerDependenciesFactory.create("svc", telegram_notifier=lambda *_: None)

    assert isinstance(deps, ErrorAnalyzerDependencies)
    assert deps.categorizer.name == "categorizer"
    assert deps.notification_sender.name == "notification"
    assert deps.recovery_reporter.name == "recovery"


def test_create_or_use_uses_all_optional_components():
    """When optional dependencies are fully provided, they should be reused."""
    opt = OptionalDependencies(
        categorizer=MagicMock(name="cat"),
        severity_evaluator=MagicMock(name="sev"),
        root_cause_identifier=MagicMock(name="root"),
        action_suggester=MagicMock(name="action"),
        notification_sender=MagicMock(name="notif"),
        recovery_reporter=MagicMock(name="recovery"),
    )

    deps = ErrorAnalyzerDependenciesFactory.create_or_use(
        "svc",
        telegram_notifier=lambda *_: None,
        optional_deps=opt,
    )

    assert deps.categorizer is opt.categorizer
    assert deps.notification_sender is opt.notification_sender
    assert deps.recovery_reporter is opt.recovery_reporter


def test_create_or_use_merges_when_optional_is_partial(monkeypatch):
    """Use provided optional components and create the rest."""
    service_deps = ErrorAnalyzerDependencies(
        categorizer=MagicMock(name="created-cat"),
        severity_evaluator=MagicMock(name="created-sev"),
        root_cause_identifier=MagicMock(name="created-root"),
        action_suggester=MagicMock(name="created-action"),
        notification_sender=MagicMock(name="created-notif"),
        recovery_reporter=MagicMock(name="created-recovery"),
    )

    called = []

    def fake_create(name, notifier):
        called.append((name, notifier))
        return service_deps

    monkeypatch.setattr(ErrorAnalyzerDependenciesFactory, "create", staticmethod(fake_create))

    optional_deps = OptionalDependencies(
        categorizer=MagicMock(name="user-cat"),
        severity_evaluator=None,
        root_cause_identifier=None,
        action_suggester=None,
        notification_sender=None,
        recovery_reporter=None,
    )

    notifier = lambda *_: None
    deps = ErrorAnalyzerDependenciesFactory.create_or_use(
        "svc",
        telegram_notifier=notifier,
        optional_deps=optional_deps,
    )

    assert deps.categorizer is optional_deps.categorizer
    assert deps.severity_evaluator is service_deps.severity_evaluator
    assert deps.root_cause_identifier is service_deps.root_cause_identifier
    assert deps.action_suggester is service_deps.action_suggester
    assert deps.notification_sender is service_deps.notification_sender
    assert called == [("svc", notifier)]
