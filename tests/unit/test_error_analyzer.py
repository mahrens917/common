import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import requests

from common.error_analyzer import ErrorAnalyzer
from common.error_analyzer_helpers.data_classes import (
    ErrorAnalysis,
    ErrorCategory,
    ErrorSeverity,
)

_TEST_COUNT_2 = 2


@pytest.mark.asyncio
async def test_analyze_and_report_error_records_history_and_notifies():
    notifier = AsyncMock()
    analyzer = ErrorAnalyzer("weather-service", telegram_notifier=notifier)

    err = ConnectionError("Timeout connecting to upstream host")
    context = {"attempt": 3, "endpoint": "orders"}

    analysis = await analyzer.analyze_and_report_error(err, context=context)

    assert analysis.category is ErrorCategory.NETWORK
    assert analysis.severity is ErrorSeverity.MEDIUM
    assert analysis.recovery_possible is True
    assert analysis.context == context
    assert analyzer.error_history == [analysis]

    notifier.assert_awaited_once()
    message = notifier.await_args.args[0]
    assert "[weather-service]" in message
    assert "Category: Network" in message
    assert "attempt=3" in message


@pytest.mark.asyncio
async def test_analyze_error_history_trims_and_marks_configuration():
    analyzer = ErrorAnalyzer("config-service")
    analyzer.max_history_size = _TEST_COUNT_2

    first = await analyzer.analyze_and_report_error(RuntimeError("configuration missing env var"))
    assert first.category is ErrorCategory.CONFIGURATION
    assert first.severity is ErrorSeverity.CRITICAL
    assert first.recovery_possible is False

    second = await analyzer.analyze_and_report_error(RuntimeError("config missing secret"))
    third = await analyzer.analyze_and_report_error(RuntimeError("configuration not found"))

    assert len(analyzer.error_history) == _TEST_COUNT_2
    assert analyzer.error_history[0].error_message == "config missing secret"
    assert analyzer.error_history[1].error_message == "configuration not found"


def _install_suppression_stub(monkeypatch, *, should_suppress: bool):
    module = types.ModuleType("common.alert_suppression_manager")

    class AlertType:
        RECOVERY = "recovery"

    decision = SimpleNamespace(
        should_suppress=should_suppress,
        reason="routine reconnection" if should_suppress else "",
    )

    manager = SimpleNamespace(should_suppress_alert=AsyncMock(return_value=decision))

    async def get_alert_suppression_manager():
        return manager

    module.AlertType = AlertType
    module.get_alert_suppression_manager = get_alert_suppression_manager

    monkeypatch.setitem(sys.modules, "common.alert_suppression_manager", module)
    if "common" in sys.modules:
        monkeypatch.setattr(
            sys.modules["common"], "alert_suppression_manager", module, raising=False
        )

    return manager


@pytest.mark.asyncio
async def test_report_recovery_suppresses_when_configured(monkeypatch):
    notifier = AsyncMock()
    analyzer = ErrorAnalyzer("monitor", telegram_notifier=notifier)
    manager = _install_suppression_stub(monkeypatch, should_suppress=True)

    await analyzer.report_recovery("Connection re-established", {"latency": 42})

    manager.should_suppress_alert.assert_awaited_once()
    notifier.assert_not_awaited()


@pytest.mark.asyncio
async def test_report_recovery_notifies_when_not_suppressed(monkeypatch):
    notifier = AsyncMock()
    analyzer = ErrorAnalyzer("monitor", telegram_notifier=notifier)
    manager = _install_suppression_stub(monkeypatch, should_suppress=False)

    await analyzer.report_recovery("Connection re-established", {"latency": 42})

    manager.should_suppress_alert.assert_awaited_once()
    notifier.assert_awaited_once()
    message = notifier.await_args.args[0]
    assert "[monitor] RECOVERY" in message
    assert "latency=42" in message


@pytest.mark.asyncio
async def test_analyze_and_report_error_detects_websocket():
    notifier = AsyncMock()
    analyzer = ErrorAnalyzer("websocket-service", telegram_notifier=notifier)

    error = RuntimeError("WebSocket abnormal closure code 1006")
    override = "websocket connection closed code 1006"
    analysis = await analyzer.analyze_and_report_error(error, custom_message=override)

    assert analysis.category is ErrorCategory.WEBSOCKET
    assert analysis.severity is ErrorSeverity.HIGH
    assert override == analysis.error_message
    assert "1006" in analysis.root_cause
    assert analyzer.error_history[-1] is analysis


@pytest.mark.asyncio
async def test_send_notification_handles_notifier_failure(caplog):
    async def failing_notifier(message):
        raise RuntimeError("telegram unavailable")

    analyzer = ErrorAnalyzer("service", telegram_notifier=failing_notifier)
    analysis = analyzer._analyze_error(
        ValueError("json parse error"), context=None, custom_message=None
    )

    caplog.set_level("ERROR")
    await analyzer._send_telegram_notification(analysis)

    assert any("Failed to send error notification" in record.message for record in caplog.records)


def test_error_analysis_to_dict_serialises_fields():
    analysis = ErrorAnalysis(
        service_name="svc",
        error_message="boom",
        error_type="RuntimeError",
        category=ErrorCategory.DATA,
        severity=ErrorSeverity.LOW,
        root_cause="Data format error",
        suggested_action="Check data",
        timestamp=1_700_000_000,
        stack_trace=None,
        context={"scope": "test"},
        recovery_possible=True,
    )

    payload = analysis.to_dict()

    assert payload["category"] == "data"
    assert payload["severity"] == "low"
    assert payload["timestamp_iso"].startswith("2023-")
    assert payload["context"] == {"scope": "test"}


@pytest.mark.parametrize(
    "error, message, expected_category, expected_severity, root_snippet, suggestion_snippet",
    [
        (
            requests.HTTPError("status code 500"),
            None,
            ErrorCategory.API,
            ErrorSeverity.MEDIUM,
            "Server internal error",
            "Check API documentation",
        ),
        (
            RuntimeError("401 unauthorized access"),
            None,
            ErrorCategory.AUTHENTICATION,
            ErrorSeverity.CRITICAL,
            "Authentication failed",
            "Verify credentials",
        ),
        (
            RuntimeError("Redis connection dropped"),
            None,
            ErrorCategory.DEPENDENCY,
            ErrorSeverity.HIGH,
            "Redis connection issue",
            "dependency service status",
        ),
        (
            ValueError("JSON decode error"),
            None,
            ErrorCategory.DATA,
            ErrorSeverity.LOW,
            "JSON parsing error",
            "Validate data source",
        ),
        (
            RuntimeError("memory exhausted while processing batch"),
            None,
            ErrorCategory.RESOURCE,
            ErrorSeverity.LOW,
            "Resource constraint",
            "Monitor system resources",
        ),
    ],
)
def test_analyze_error_categorizes_various_types(
    error, message, expected_category, expected_severity, root_snippet, suggestion_snippet
):
    analyzer = ErrorAnalyzer("svc")
    analysis = analyzer._analyze_error(error, context=None, custom_message=message)

    assert analysis.category is expected_category
    assert analysis.severity is expected_severity
    assert root_snippet in analysis.root_cause
    assert suggestion_snippet in analysis.suggested_action
    assert analysis.recovery_possible is (expected_category != ErrorCategory.CONFIGURATION)


def test_analyze_error_uses_context_for_websocket_close_code():
    analyzer = ErrorAnalyzer("ws")
    error = RuntimeError("WebSocket connection closed unexpectedly")
    context = {"close_code": 1006}

    analysis = analyzer._analyze_error(error, context=context, custom_message=None)

    assert "1006 abnormal closure" in analysis.root_cause
    assert "reconnection" in analysis.suggested_action.lower()


def test_analyze_error_defaults_to_unknown_category():
    analyzer = ErrorAnalyzer("svc")
    error = RuntimeError("Unrecognized failure without keywords")

    analysis = analyzer._analyze_error(error, context=None, custom_message=None)

    assert analysis.category is ErrorCategory.UNKNOWN
    assert analysis.severity is ErrorSeverity.LOW
    assert analysis.recovery_possible is True
    assert analysis.root_cause.startswith("Unknown error")
