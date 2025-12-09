import pytest

from src.common.alert_suppression_manager_helpers.alert_evaluator import (
    AlertEvaluator,
    SuppressionContext,
    SuppressionRule,
)
from src.common.alert_suppression_manager_helpers.decision_coordinator import (
    DecisionCoordinator,
)
from src.common.alert_suppression_manager_helpers.dependency_initializer import (
    DependencyInitializer,
)
from src.common.alert_suppression_manager_helpers.error_classifier_adapter import (
    ErrorClassifierAdapter,
)
from src.common.alert_suppression_manager_helpers.suppression_tracker import (
    AlertType,
    SuppressionDecision,
    SuppressionTracker,
)


class _StubContextBuilder:
    def __init__(self, context: SuppressionContext):
        self.context = context
        self.calls: list[tuple] = []

    async def build_context(self, **kwargs) -> SuppressionContext:  # type: ignore[override]
        self.calls.append(tuple(sorted(kwargs.keys())))
        return self.context


@pytest.mark.asyncio
async def test_decision_coordinator_handles_disabled_rule():
    rule = SuppressionRule(enabled=False)
    tracker = SuppressionTracker()
    evaluator = AlertEvaluator(rule)
    context = SuppressionContext(
        service_type="svc",
        is_in_reconnection=False,
        is_in_grace_period=False,
        reconnection_duration=None,
        grace_period_remaining_seconds=None,
        is_reconnection_error=False,
    )
    coordinator = DecisionCoordinator(
        rule,
        tracker,
        evaluator,
        _StubContextBuilder(context),
    )

    decision = await coordinator.make_decision(
        service_name="svc",
        service_type="primary",
        alert_type=AlertType.ERROR_LOG,
        error_message="boom",
        state_tracker=object(),
        error_classifier=object(),
    )

    assert decision == SuppressionDecision(
        should_suppress=False,
        reason="Alert suppression is disabled",
        service_name="svc",
        alert_type=AlertType.ERROR_LOG,
        suppression_duration_seconds=None,
        grace_period_remaining_seconds=None,
    )
    assert tracker.has_history()


@pytest.mark.asyncio
async def test_decision_coordinator_rejects_unknown_alert_type():
    rule = SuppressionRule()
    tracker = SuppressionTracker()
    coordinator = DecisionCoordinator(
        rule,
        tracker,
        AlertEvaluator(rule),
        _StubContextBuilder(
            SuppressionContext(
                service_type="svc",
                is_in_reconnection=False,
                is_in_grace_period=False,
                reconnection_duration=None,
                grace_period_remaining_seconds=None,
                is_reconnection_error=False,
            )
        ),
    )

    decision = await coordinator.make_decision(
        service_name="svc",
        service_type="primary",
        alert_type=AlertType.PROCESS_STATUS,
        error_message=None,
        state_tracker=object(),
        error_classifier=object(),
    )

    assert not decision.should_suppress
    assert "not configured" in decision.reason
    assert tracker.get_recent_decisions()[0].alert_type is AlertType.PROCESS_STATUS


@pytest.mark.asyncio
async def test_decision_coordinator_builds_suppressed_decision():
    rule = SuppressionRule()
    tracker = SuppressionTracker()
    evaluator = AlertEvaluator(rule)
    context = SuppressionContext(
        service_type="svc",
        is_in_reconnection=True,
        is_in_grace_period=False,
        reconnection_duration=3.0,
        grace_period_remaining_seconds=None,
        is_reconnection_error=True,
    )
    stub_builder = _StubContextBuilder(context)
    coordinator = DecisionCoordinator(rule, tracker, evaluator, stub_builder)

    decision = await coordinator.make_decision(
        service_name="svc",
        service_type="primary",
        alert_type=AlertType.ERROR_LOG,
        error_message="connection reset",
        state_tracker=object(),
        error_classifier=object(),
    )

    assert decision.should_suppress
    assert "error matches reconnection pattern" in decision.reason
    assert stub_builder.calls  # ensure the builder was invoked
    assert tracker.has_history()


@pytest.mark.asyncio
async def test_dependency_initializer_initializes_and_requires(monkeypatch):
    initializer = DependencyInitializer()

    async def fake_state_tracker():
        return "state-tracker"

    def fake_error_classifier():
        return "classifier"

    monkeypatch.setattr(
        "src.common.alert_suppression_manager_helpers.dependency_initializer.get_connection_state_tracker",
        fake_state_tracker,
    )
    monkeypatch.setattr(
        "src.common.alert_suppression_manager_helpers.dependency_initializer.get_error_classifier",
        fake_error_classifier,
    )

    await initializer.initialize()
    assert initializer.state_tracker == "state-tracker"
    assert initializer.error_classifier == "classifier"
    assert initializer.require_dependencies() == ("state-tracker", "classifier")

    with pytest.raises(RuntimeError):
        DependencyInitializer().require_dependencies()


def test_error_classifier_adapter_delegates():
    """Test that ErrorClassifierAdapter correctly delegates to underlying classifier."""
    captured: list[tuple[str, str]] = []

    class DummyClassifier:
        def classify_error_type(self, service: str, message: str) -> str:
            captured.append((service, message))
            return "classified"

        def is_reconnection_error(self, service: str, message: str) -> bool:
            captured.append((service + "-reconnect", message))
            return True

    adapter = ErrorClassifierAdapter(DummyClassifier())

    assert adapter.classify_error_type("svc", "msg") == "classified"
    assert adapter.is_reconnection_error("svc", "msg")
    assert captured == [("svc", "msg"), ("svc-reconnect", "msg")]
