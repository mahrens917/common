"""Tests for error_matcher module."""

from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest

from src.common.reconnection_error_patterns_helpers.error_matcher import ErrorMatcher
from src.common.reconnection_error_patterns_helpers.service_type_manager import ServiceType


class TestErrorMatcherInit:
    """Tests for ErrorMatcher initialization."""

    def test_init_stores_compiled_patterns(self) -> None:
        """Stores compiled patterns dictionary."""
        patterns = {
            ServiceType.WEBSOCKET: [re.compile("connection lost", re.IGNORECASE)],
            ServiceType.REST: [re.compile("timeout", re.IGNORECASE)],
        }

        matcher = ErrorMatcher(patterns)

        assert matcher.compiled_patterns == patterns

    def test_init_with_empty_patterns(self) -> None:
        """Initializes with empty patterns dictionary."""
        matcher = ErrorMatcher({})

        assert matcher.compiled_patterns == {}


class TestErrorMatcherMatchesPattern:
    """Tests for ErrorMatcher.matches_pattern method."""

    def test_returns_false_for_empty_message(self) -> None:
        """Returns (False, None) for empty error message."""
        patterns = {ServiceType.WEBSOCKET: [re.compile("error", re.IGNORECASE)]}
        matcher = ErrorMatcher(patterns)

        matches, pattern = matcher.matches_pattern(ServiceType.WEBSOCKET, "")

        assert matches is False
        assert pattern is None

    def test_returns_false_for_unknown_service_type(self) -> None:
        """Returns (False, None) for UNKNOWN service type."""
        patterns = {ServiceType.WEBSOCKET: [re.compile("error", re.IGNORECASE)]}
        matcher = ErrorMatcher(patterns)

        matches, pattern = matcher.matches_pattern(ServiceType.UNKNOWN, "Connection error occurred")

        assert matches is False
        assert pattern is None

    def test_returns_true_when_pattern_matches(self) -> None:
        """Returns (True, pattern_string) when pattern matches."""
        patterns = {ServiceType.WEBSOCKET: [re.compile("connection lost", re.IGNORECASE)]}
        matcher = ErrorMatcher(patterns)

        matches, pattern = matcher.matches_pattern(
            ServiceType.WEBSOCKET, "WebSocket connection lost unexpectedly"
        )

        assert matches is True
        assert pattern == "connection lost"

    def test_returns_false_when_no_pattern_matches(self) -> None:
        """Returns (False, None) when no pattern matches."""
        patterns = {ServiceType.WEBSOCKET: [re.compile("connection lost", re.IGNORECASE)]}
        matcher = ErrorMatcher(patterns)

        matches, pattern = matcher.matches_pattern(ServiceType.WEBSOCKET, "Authentication failed")

        assert matches is False
        assert pattern is None

    def test_returns_false_when_service_type_not_in_patterns(self) -> None:
        """Returns (False, None) when service type not in patterns dictionary."""
        patterns = {ServiceType.WEBSOCKET: [re.compile("error", re.IGNORECASE)]}
        matcher = ErrorMatcher(patterns)

        matches, pattern = matcher.matches_pattern(ServiceType.REST, "Connection error")

        assert matches is False
        assert pattern is None

    def test_matches_first_matching_pattern(self) -> None:
        """Returns first matching pattern when multiple could match."""
        patterns = {
            ServiceType.WEBSOCKET: [
                re.compile("connection", re.IGNORECASE),
                re.compile("error", re.IGNORECASE),
            ]
        }
        matcher = ErrorMatcher(patterns)

        matches, pattern = matcher.matches_pattern(
            ServiceType.WEBSOCKET, "Connection error occurred"
        )

        assert matches is True
        assert pattern == "connection"

    def test_case_insensitive_matching(self) -> None:
        """Matches patterns case-insensitively."""
        patterns = {ServiceType.WEBSOCKET: [re.compile("connection lost", re.IGNORECASE)]}
        matcher = ErrorMatcher(patterns)

        matches, pattern = matcher.matches_pattern(ServiceType.WEBSOCKET, "CONNECTION LOST")

        assert matches is True
        assert pattern == "connection lost"

    def test_matches_with_regex_patterns(self) -> None:
        """Matches regex patterns correctly."""
        patterns = {ServiceType.SCRAPER: [re.compile(r"rate.*limit", re.IGNORECASE)]}
        matcher = ErrorMatcher(patterns)

        matches, pattern = matcher.matches_pattern(ServiceType.SCRAPER, "Rate limit exceeded")

        assert matches is True
        assert pattern == r"rate.*limit"


class TestErrorMatcherCheckWithLogging:
    """Tests for ErrorMatcher.check_with_logging method."""

    def test_returns_true_when_matches(self) -> None:
        """Returns True when pattern matches."""
        patterns = {ServiceType.WEBSOCKET: [re.compile("connection lost", re.IGNORECASE)]}
        matcher = ErrorMatcher(patterns)

        result = matcher.check_with_logging(
            "kalshi", ServiceType.WEBSOCKET, "WebSocket connection lost"
        )

        assert result is True

    def test_returns_false_when_no_match(self) -> None:
        """Returns False when no pattern matches."""
        patterns = {ServiceType.WEBSOCKET: [re.compile("connection lost", re.IGNORECASE)]}
        matcher = ErrorMatcher(patterns)

        result = matcher.check_with_logging(
            "kalshi", ServiceType.WEBSOCKET, "Authentication failed"
        )

        assert result is False

    def test_logs_debug_when_matches(self) -> None:
        """Logs debug message when pattern matches."""
        patterns = {ServiceType.WEBSOCKET: [re.compile("connection lost", re.IGNORECASE)]}
        matcher = ErrorMatcher(patterns)

        with patch(
            "src.common.reconnection_error_patterns_helpers.error_matcher.logger"
        ) as mock_logger:
            matcher.check_with_logging("kalshi", ServiceType.WEBSOCKET, "WebSocket connection lost")

            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args[0][0]
            assert "Reconnection error detected" in call_args
            assert "kalshi" in call_args

    def test_logs_debug_when_no_match(self) -> None:
        """Logs debug message when no pattern matches."""
        patterns = {ServiceType.WEBSOCKET: [re.compile("connection lost", re.IGNORECASE)]}
        matcher = ErrorMatcher(patterns)

        with patch(
            "src.common.reconnection_error_patterns_helpers.error_matcher.logger"
        ) as mock_logger:
            matcher.check_with_logging("kalshi", ServiceType.WEBSOCKET, "Authentication failed")

            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args[0][0]
            assert "No reconnection pattern match" in call_args
            assert "kalshi" in call_args

    def test_truncates_long_error_messages_in_logs(self) -> None:
        """Truncates error messages longer than 100 characters in logs."""
        patterns = {ServiceType.WEBSOCKET: [re.compile("connection", re.IGNORECASE)]}
        matcher = ErrorMatcher(patterns)
        long_message = "Connection lost: " + "x" * 200

        with patch(
            "src.common.reconnection_error_patterns_helpers.error_matcher.logger"
        ) as mock_logger:
            matcher.check_with_logging("kalshi", ServiceType.WEBSOCKET, long_message)

            call_args = mock_logger.debug.call_args[0][0]
            # Should contain "..." indicating truncation
            assert "..." in call_args


class TestErrorMatcherWithMultipleServiceTypes:
    """Tests for ErrorMatcher with multiple service types."""

    def test_matches_correct_service_type_patterns(self) -> None:
        """Matches patterns for the correct service type."""
        patterns = {
            ServiceType.WEBSOCKET: [re.compile("websocket", re.IGNORECASE)],
            ServiceType.REST: [re.compile("http", re.IGNORECASE)],
            ServiceType.SCRAPER: [re.compile("scrape", re.IGNORECASE)],
        }
        matcher = ErrorMatcher(patterns)

        ws_matches, _ = matcher.matches_pattern(ServiceType.WEBSOCKET, "WebSocket error")
        rest_matches, _ = matcher.matches_pattern(ServiceType.REST, "HTTP timeout")
        scraper_matches, _ = matcher.matches_pattern(ServiceType.SCRAPER, "Scrape failed")

        assert ws_matches is True
        assert rest_matches is True
        assert scraper_matches is True

    def test_does_not_cross_match_service_types(self) -> None:
        """Does not match patterns from different service types."""
        patterns = {
            ServiceType.WEBSOCKET: [re.compile("websocket", re.IGNORECASE)],
            ServiceType.REST: [re.compile("http", re.IGNORECASE)],
        }
        matcher = ErrorMatcher(patterns)

        # REST service should not match websocket pattern
        matches, _ = matcher.matches_pattern(ServiceType.REST, "WebSocket error")

        assert matches is False
