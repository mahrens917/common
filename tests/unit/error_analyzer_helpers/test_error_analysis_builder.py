"""Tests for error analysis builder."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from common.error_analyzer_helpers.data_classes import ErrorCategory, ErrorSeverity
from common.error_analyzer_helpers.error_analysis_builder import ErrorAnalysisBuilder


class TestErrorAnalysisBuilder:
    """Tests for ErrorAnalysisBuilder class."""

    def test_init_stores_all_components(self) -> None:
        """ErrorAnalysisBuilder stores all provided components."""
        categorizer = MagicMock()
        severity_evaluator = MagicMock()
        root_cause_identifier = MagicMock()
        action_suggester = MagicMock()

        builder = ErrorAnalysisBuilder(
            service_name="test_service",
            categorizer=categorizer,
            severity_evaluator=severity_evaluator,
            root_cause_identifier=root_cause_identifier,
            action_suggester=action_suggester,
        )

        assert builder.service_name == "test_service"
        assert builder.categorizer is categorizer
        assert builder.severity_evaluator is severity_evaluator
        assert builder.root_cause_identifier is root_cause_identifier
        assert builder.action_suggester is action_suggester

    def test_build_analysis_creates_error_analysis(self) -> None:
        """build_analysis creates ErrorAnalysis with all fields."""
        categorizer = MagicMock()
        categorizer.categorize_error.return_value = ErrorCategory.NETWORK

        severity_evaluator = MagicMock()
        severity_evaluator.determine_severity.return_value = ErrorSeverity.HIGH

        root_cause_identifier = MagicMock()
        root_cause_identifier.identify_root_cause.return_value = "Network timeout"

        action_suggester = MagicMock()
        action_suggester.suggest_action.return_value = "Retry with backoff"

        builder = ErrorAnalysisBuilder(
            service_name="test_service",
            categorizer=categorizer,
            severity_evaluator=severity_evaluator,
            root_cause_identifier=root_cause_identifier,
            action_suggester=action_suggester,
        )

        error = ConnectionError("Connection refused")
        context = {"host": "localhost"}
        custom_message = "Custom error message"

        with patch("common.error_analyzer_helpers.error_analysis_builder.time") as mock_time:
            mock_time.time.return_value = 1234567890.0
            result = builder.build_analysis(error, context, custom_message)

        assert result.service_name == "test_service"
        assert result.error_message == custom_message
        assert result.error_type == "ConnectionError"
        assert result.category == ErrorCategory.NETWORK
        assert result.severity == ErrorSeverity.HIGH
        assert result.root_cause == "Network timeout"
        assert result.suggested_action == "Retry with backoff"
        assert result.timestamp == 1234567890.0
        assert result.context == context
        assert result.recovery_possible is True

    def test_build_analysis_uses_str_error_when_no_custom_message(self) -> None:
        """build_analysis uses str(error) when custom_message is None."""
        categorizer = MagicMock()
        categorizer.categorize_error.return_value = ErrorCategory.DATA

        severity_evaluator = MagicMock()
        severity_evaluator.determine_severity.return_value = ErrorSeverity.LOW

        root_cause_identifier = MagicMock()
        root_cause_identifier.identify_root_cause.return_value = "Invalid data"

        action_suggester = MagicMock()
        action_suggester.suggest_action.return_value = "Check input"

        builder = ErrorAnalysisBuilder(
            service_name="data_service",
            categorizer=categorizer,
            severity_evaluator=severity_evaluator,
            root_cause_identifier=root_cause_identifier,
            action_suggester=action_suggester,
        )

        error = ValueError("Invalid value")

        result = builder.build_analysis(error, {}, None)

        assert result.error_message == "Invalid value"

    def test_build_analysis_recovery_not_possible_for_configuration(self) -> None:
        """build_analysis sets recovery_possible=False for CONFIGURATION category."""
        categorizer = MagicMock()
        categorizer.categorize_error.return_value = ErrorCategory.CONFIGURATION

        severity_evaluator = MagicMock()
        severity_evaluator.determine_severity.return_value = ErrorSeverity.CRITICAL

        root_cause_identifier = MagicMock()
        root_cause_identifier.identify_root_cause.return_value = "Missing config"

        action_suggester = MagicMock()
        action_suggester.suggest_action.return_value = "Fix configuration"

        builder = ErrorAnalysisBuilder(
            service_name="config_service",
            categorizer=categorizer,
            severity_evaluator=severity_evaluator,
            root_cause_identifier=root_cause_identifier,
            action_suggester=action_suggester,
        )

        error = FileNotFoundError("config.json not found")

        result = builder.build_analysis(error, {}, None)

        assert result.category == ErrorCategory.CONFIGURATION
        assert result.recovery_possible is False

    def test_build_analysis_includes_stack_trace(self) -> None:
        """build_analysis includes stack trace."""
        categorizer = MagicMock()
        categorizer.categorize_error.return_value = ErrorCategory.UNKNOWN

        severity_evaluator = MagicMock()
        severity_evaluator.determine_severity.return_value = ErrorSeverity.MEDIUM

        root_cause_identifier = MagicMock()
        root_cause_identifier.identify_root_cause.return_value = "Unknown cause"

        action_suggester = MagicMock()
        action_suggester.suggest_action.return_value = "Investigate"

        builder = ErrorAnalysisBuilder(
            service_name="test_service",
            categorizer=categorizer,
            severity_evaluator=severity_evaluator,
            root_cause_identifier=root_cause_identifier,
            action_suggester=action_suggester,
        )

        error = RuntimeError("Test error")

        result = builder.build_analysis(error, {}, None)

        assert result.stack_trace is not None
        assert isinstance(result.stack_trace, str)

    def test_build_analysis_calls_all_analyzers(self) -> None:
        """build_analysis calls all analyzer methods with correct arguments."""
        categorizer = MagicMock()
        categorizer.categorize_error.return_value = ErrorCategory.API

        severity_evaluator = MagicMock()
        severity_evaluator.determine_severity.return_value = ErrorSeverity.HIGH

        root_cause_identifier = MagicMock()
        root_cause_identifier.identify_root_cause.return_value = "API error"

        action_suggester = MagicMock()
        action_suggester.suggest_action.return_value = "Retry"

        builder = ErrorAnalysisBuilder(
            service_name="api_service",
            categorizer=categorizer,
            severity_evaluator=severity_evaluator,
            root_cause_identifier=root_cause_identifier,
            action_suggester=action_suggester,
        )

        error = Exception("API failure")
        context = {"endpoint": "/api/v1"}
        custom_message = "API call failed"

        builder.build_analysis(error, context, custom_message)

        categorizer.categorize_error.assert_called_once_with(error, custom_message, context)
        severity_evaluator.determine_severity.assert_called_once_with(error, ErrorCategory.API, context)
        root_cause_identifier.identify_root_cause.assert_called_once_with(error, custom_message, ErrorCategory.API, context)
        action_suggester.suggest_action.assert_called_once_with(error, ErrorCategory.API, "API error")
