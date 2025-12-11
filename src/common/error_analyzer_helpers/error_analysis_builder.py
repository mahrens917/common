"""Error analysis builder for ErrorAnalyzer."""

import time
import traceback

from .data_classes import ErrorAnalysis, ErrorCategory


class ErrorAnalysisBuilder:
    """Builds comprehensive error analysis from exceptions."""

    def __init__(self, service_name, categorizer, severity_evaluator, root_cause_identifier, action_suggester):
        """Initialize error analysis builder."""
        self.service_name = service_name
        self.categorizer = categorizer
        self.severity_evaluator = severity_evaluator
        self.root_cause_identifier = root_cause_identifier
        self.action_suggester = action_suggester

    def build_analysis(self, error, context, custom_message) -> ErrorAnalysis:
        """Analyze an error and determine root cause."""
        error_type = type(error).__name__
        error_message = custom_message or str(error)
        stack_trace = traceback.format_exc()

        category = self.categorizer.categorize_error(error, error_message, context)
        severity = self.severity_evaluator.determine_severity(error, category, context)
        root_cause = self.root_cause_identifier.identify_root_cause(error, error_message, category, context)
        suggested_action = self.action_suggester.suggest_action(error, category, root_cause)
        recovery_possible = category != ErrorCategory.CONFIGURATION

        return ErrorAnalysis(
            service_name=self.service_name,
            error_message=error_message,
            error_type=error_type,
            category=category,
            severity=severity,
            root_cause=root_cause,
            suggested_action=suggested_action,
            timestamp=time.time(),
            stack_trace=stack_trace,
            context=context,
            recovery_possible=recovery_possible,
        )
