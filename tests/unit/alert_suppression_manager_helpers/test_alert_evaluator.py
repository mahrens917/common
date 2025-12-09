"""Tests for alert evaluator."""

import pytest

from src.common.alert_suppression_manager_helpers.alert_evaluator import (
    AlertEvaluator,
    SuppressionContext,
    SuppressionRule,
    _evaluate_during_reconnection,
    _evaluate_recovery_alert,
)
from src.common.alert_suppression_manager_helpers.suppression_tracker import AlertType


def test_suppression_rule_defaults():
    """Test SuppressionRule default values."""
    rule = SuppressionRule()

    assert rule.enabled is True
    assert rule.grace_period_seconds == 300
    assert rule.require_reconnection_error_pattern is True
    assert rule.max_suppression_duration_seconds == 1800
    assert AlertType.ERROR_LOG in rule.suppressed_alert_types
    assert AlertType.STALE_LOG in rule.suppressed_alert_types
    assert AlertType.MESSAGE_METRICS in rule.suppressed_alert_types


def test_suppression_rule_custom_values():
    """Test creating SuppressionRule with custom values."""
    rule = SuppressionRule(
        enabled=False,
        grace_period_seconds=600,
        suppressed_alert_types={AlertType.RECOVERY},
        require_reconnection_error_pattern=False,
        max_suppression_duration_seconds=3600,
    )

    assert rule.enabled is False
    assert rule.grace_period_seconds == 600
    assert rule.suppressed_alert_types == {AlertType.RECOVERY}
    assert rule.require_reconnection_error_pattern is False
    assert rule.max_suppression_duration_seconds == 3600


def test_suppression_context_creation():
    """Test creating SuppressionContext."""
    context = SuppressionContext(
        service_type="websocket",
        is_in_reconnection=True,
        is_in_grace_period=False,
        reconnection_duration=45.0,
        grace_period_remaining_seconds=None,
        is_reconnection_error=True,
    )

    assert context.service_type == "websocket"
    assert context.is_in_reconnection is True
    assert context.is_in_grace_period is False
    assert context.reconnection_duration == 45.0
    assert context.grace_period_remaining_seconds is None
    assert context.is_reconnection_error is True


def test_alert_evaluator_initialization():
    """Test AlertEvaluator initialization."""
    rule = SuppressionRule()
    evaluator = AlertEvaluator(rule)

    assert evaluator.suppression_rule == rule


def test_is_alert_type_supported():
    """Test checking if alert type is supported."""
    rule = SuppressionRule(suppressed_alert_types={AlertType.ERROR_LOG, AlertType.STALE_LOG})
    evaluator = AlertEvaluator(rule)

    assert evaluator.is_alert_type_supported(AlertType.ERROR_LOG) is True
    assert evaluator.is_alert_type_supported(AlertType.STALE_LOG) is True
    assert evaluator.is_alert_type_supported(AlertType.RECOVERY) is False


def test_evaluate_recovery_alert_in_reconnection():
    """Test evaluating recovery alert during reconnection."""
    context = SuppressionContext(
        service_type="websocket",
        is_in_reconnection=True,
        is_in_grace_period=False,
        reconnection_duration=30.0,
        grace_period_remaining_seconds=None,
        is_reconnection_error=False,
    )

    should_suppress, reason_parts = _evaluate_recovery_alert(context)

    assert should_suppress is True
    assert "reconnection mode" in " ".join(reason_parts)
    assert "recovery notification suppressed" in " ".join(reason_parts)


def test_evaluate_recovery_alert_in_grace_period():
    """Test evaluating recovery alert during grace period."""
    context = SuppressionContext(
        service_type="websocket",
        is_in_reconnection=False,
        is_in_grace_period=True,
        reconnection_duration=None,
        grace_period_remaining_seconds=100.0,
        is_reconnection_error=False,
    )

    should_suppress, reason_parts = _evaluate_recovery_alert(context)

    assert should_suppress is True
    assert "post-reconnection grace period" in " ".join(reason_parts)


def test_evaluate_recovery_alert_not_suppressed():
    """Test evaluating recovery alert when not in reconnection or grace period."""
    context = SuppressionContext(
        service_type="websocket",
        is_in_reconnection=False,
        is_in_grace_period=False,
        reconnection_duration=None,
        grace_period_remaining_seconds=None,
        is_reconnection_error=False,
    )

    should_suppress, reason_parts = _evaluate_recovery_alert(context)

    assert should_suppress is False
    assert reason_parts == []


def test_evaluate_during_reconnection_within_max_duration():
    """Test evaluating during reconnection within max duration."""
    rule = SuppressionRule(max_suppression_duration_seconds=1800)
    context = SuppressionContext(
        service_type="websocket",
        is_in_reconnection=True,
        is_in_grace_period=False,
        reconnection_duration=300.0,  # 5 minutes
        grace_period_remaining_seconds=None,
        is_reconnection_error=False,
    )

    should_suppress, reason_parts = _evaluate_during_reconnection(rule, context)

    assert should_suppress is True
    assert "service is in reconnection mode" in " ".join(reason_parts)
    assert "duration: 300.0s" in " ".join(reason_parts)


def test_evaluate_during_reconnection_exceeds_max_duration():
    """Test evaluating during reconnection that exceeds max duration."""
    rule = SuppressionRule(max_suppression_duration_seconds=1800)
    context = SuppressionContext(
        service_type="websocket",
        is_in_reconnection=True,
        is_in_grace_period=False,
        reconnection_duration=2000.0,  # Over 30 minutes
        grace_period_remaining_seconds=None,
        is_reconnection_error=False,
    )

    should_suppress, reason_parts = _evaluate_during_reconnection(rule, context)

    assert should_suppress is False
    assert "exceeds max suppression time" in " ".join(reason_parts)


def test_evaluate_during_reconnection_no_duration():
    """Test evaluating during reconnection with no duration."""
    rule = SuppressionRule(max_suppression_duration_seconds=1800)
    context = SuppressionContext(
        service_type="websocket",
        is_in_reconnection=True,
        is_in_grace_period=False,
        reconnection_duration=None,
        grace_period_remaining_seconds=None,
        is_reconnection_error=False,
    )

    should_suppress, reason_parts = _evaluate_during_reconnection(rule, context)

    assert should_suppress is True
    assert "service is in reconnection mode" in " ".join(reason_parts)


def test_build_decision_reconnection_error():
    """Test building decision for reconnection error."""
    rule = SuppressionRule()
    evaluator = AlertEvaluator(rule)

    context = SuppressionContext(
        service_type="websocket",
        is_in_reconnection=True,
        is_in_grace_period=False,
        reconnection_duration=30.0,
        grace_period_remaining_seconds=None,
        is_reconnection_error=True,
    )

    decision = evaluator.build_decision(
        service_name="kalshi",
        alert_type=AlertType.ERROR_LOG,
        context=context,
        error_message="Connection timeout",
    )

    assert decision.should_suppress is True
    assert "error matches reconnection pattern" in decision.reason
    assert decision.service_name == "kalshi"
    assert decision.alert_type == AlertType.ERROR_LOG


def test_build_decision_recovery_alert():
    """Test building decision for recovery alert."""
    rule = SuppressionRule()
    evaluator = AlertEvaluator(rule)

    context = SuppressionContext(
        service_type="websocket",
        is_in_reconnection=True,
        is_in_grace_period=False,
        reconnection_duration=30.0,
        grace_period_remaining_seconds=None,
        is_reconnection_error=False,
    )

    decision = evaluator.build_decision(
        service_name="weather",
        alert_type=AlertType.RECOVERY,
        context=context,
        error_message=None,
    )

    assert decision.should_suppress is True
    assert "reconnection mode" in decision.reason


def test_build_decision_in_grace_period():
    """Test building decision during grace period."""
    rule = SuppressionRule()
    evaluator = AlertEvaluator(rule)

    context = SuppressionContext(
        service_type="websocket",
        is_in_reconnection=False,
        is_in_grace_period=True,
        reconnection_duration=None,
        grace_period_remaining_seconds=150.0,
        is_reconnection_error=False,
    )

    decision = evaluator.build_decision(
        service_name="deribit",
        alert_type=AlertType.ERROR_LOG,
        context=context,
        error_message=None,
    )

    assert decision.should_suppress is True
    assert "post-reconnection grace period" in decision.reason
    assert decision.grace_period_remaining_seconds == 150.0


def test_build_decision_no_suppression():
    """Test building decision when no suppression conditions met."""
    rule = SuppressionRule()
    evaluator = AlertEvaluator(rule)

    context = SuppressionContext(
        service_type="websocket",
        is_in_reconnection=False,
        is_in_grace_period=False,
        reconnection_duration=None,
        grace_period_remaining_seconds=None,
        is_reconnection_error=False,
    )

    decision = evaluator.build_decision(
        service_name="kalshi",
        alert_type=AlertType.ERROR_LOG,
        context=context,
        error_message=None,
    )

    assert decision.should_suppress is False
    assert "no suppression conditions met" in decision.reason
