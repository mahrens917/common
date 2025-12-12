"""
Universal enhanced error analysis and Telegram reporting system.

This module provides detailed error analysis, root cause identification,
and automatic Telegram notifications for all services.
"""

import logging
import time
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .error_analyzer_helpers.data_classes import ErrorAnalysis, ErrorCategory, ErrorSeverity
from .error_analyzer_helpers.dependencies_factory import (
    ErrorAnalyzerDependencies,
    ErrorAnalyzerDependenciesFactory,
)

logger = logging.getLogger(__name__)

DEFAULT_ERROR_HISTORY_SIZE = 100


@dataclass(frozen=True)
class ErrorAnalysisContext:
    """Context for error analysis operations."""

    service_name: str
    error: Exception
    context: Optional[Dict[str, Any]]
    custom_message: Optional[str]


class ErrorAnalyzer:
    """
    Universal error analyzer for all services.

    Coordinates multiple helper components to analyze errors, identify root causes,
    and send automatic Telegram notifications.
    """

    def __init__(
        self,
        service_name: str,
        telegram_notifier: Optional[Callable] = None,
        *,
        dependencies: Optional[ErrorAnalyzerDependencies] = None,
    ):
        """Initialize error analyzer."""
        self.service_name = service_name
        self.telegram_notifier = telegram_notifier
        self.error_history: List[ErrorAnalysis] = []
        self.max_history_size = DEFAULT_ERROR_HISTORY_SIZE
        deps = dependencies or ErrorAnalyzerDependenciesFactory.create(service_name, telegram_notifier)
        self.categorizer = deps.categorizer
        self.severity_evaluator = deps.severity_evaluator
        self.root_cause_identifier = deps.root_cause_identifier
        self.action_suggester = deps.action_suggester
        self.notification_sender = deps.notification_sender
        self.recovery_reporter = deps.recovery_reporter

    async def analyze_and_report_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        custom_message: Optional[str] = None,
    ) -> ErrorAnalysis:
        """Analyze an error and send Telegram notification."""
        analysis_context = ErrorAnalysisContext(
            service_name=self.service_name,
            error=error,
            context=context,
            custom_message=custom_message,
        )
        components = AnalysisComponents(
            categorizer=self.categorizer,
            severity_evaluator=self.severity_evaluator,
            root_cause_identifier=self.root_cause_identifier,
            action_suggester=self.action_suggester,
        )
        analysis = _analyze_error_event(
            analysis_context=analysis_context,
            components=components,
        )

        self.error_history.append(analysis)
        if len(self.error_history) > self.max_history_size:
            self.error_history.pop(0)

        await self._send_telegram_notification(analysis)
        _log_error_analysis_result(analysis)
        return analysis

    async def report_recovery(self, recovery_message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Report service recovery."""
        await self.recovery_reporter.report_recovery(recovery_message, context)

    def _analyze_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        custom_message: Optional[str] = None,
    ) -> ErrorAnalysis:
        """Synchronous error analysis without notification."""
        analysis_context = ErrorAnalysisContext(
            service_name=self.service_name,
            error=error,
            context=context,
            custom_message=custom_message,
        )
        components = AnalysisComponents(
            categorizer=self.categorizer,
            severity_evaluator=self.severity_evaluator,
            root_cause_identifier=self.root_cause_identifier,
            action_suggester=self.action_suggester,
        )
        return _analyze_error_event(
            analysis_context=analysis_context,
            components=components,
        )

    async def _send_telegram_notification(self, analysis: ErrorAnalysis) -> None:
        """Send a Telegram notification and log failures without raising."""
        try:
            await self.notification_sender.send_telegram_notification(analysis)
        except OSError:  # policy_guard: allow-silent-handler
            logger.exception("Failed to send error notification")


@dataclass(frozen=True)
class AnalysisComponents:
    """Components needed for error analysis."""

    categorizer: Any
    severity_evaluator: Any
    root_cause_identifier: Any
    action_suggester: Any


def _analyze_error_event(
    *,
    analysis_context: ErrorAnalysisContext,
    components: AnalysisComponents,
) -> ErrorAnalysis:
    """Build the structured ErrorAnalysis payload."""
    error_type = type(analysis_context.error).__name__
    error_message = analysis_context.custom_message or str(analysis_context.error)
    stack_trace = traceback.format_exc()

    category = components.categorizer.categorize_error(analysis_context.error, error_message, analysis_context.context)
    severity = components.severity_evaluator.determine_severity(analysis_context.error, category, analysis_context.context)
    root_cause = components.root_cause_identifier.identify_root_cause(
        analysis_context.error, error_message, category, analysis_context.context
    )
    suggested_action = components.action_suggester.suggest_action(analysis_context.error, category, root_cause)
    recovery_possible = category != ErrorCategory.CONFIGURATION

    return ErrorAnalysis(
        service_name=analysis_context.service_name,
        error_message=error_message,
        error_type=error_type,
        category=category,
        severity=severity,
        root_cause=root_cause,
        suggested_action=suggested_action,
        timestamp=time.time(),
        stack_trace=stack_trace,
        context=analysis_context.context,
        recovery_possible=recovery_possible,
    )


def _log_error_analysis_result(analysis: ErrorAnalysis) -> None:
    """Log analysis results with severity-aware verbosity."""
    severity_levels = {
        ErrorSeverity.LOW: logging.WARNING,
        ErrorSeverity.MEDIUM: logging.ERROR,
        ErrorSeverity.HIGH: logging.ERROR,
        ErrorSeverity.CRITICAL: logging.CRITICAL,
    }
    log_level = severity_levels.get(analysis.severity, logging.ERROR)

    message = f"[{analysis.service_name}] {analysis.category.value.upper()} ERROR: {analysis.error_message}"
    message += f" | Root Cause: {analysis.root_cause} | Action: {analysis.suggested_action}"
    logger.log(log_level, message)

    if analysis.stack_trace and log_level >= logging.ERROR:
        logger.error(f"[{analysis.service_name}] Stack trace:\n{analysis.stack_trace}")
