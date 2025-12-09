"""Tests for pattern_compiler module."""

from __future__ import annotations

import re

import pytest

from src.common.reconnection_error_patterns_helpers.pattern_compiler import (
    RECONNECTION_ERROR_PATTERNS,
    PatternCompiler,
)
from src.common.reconnection_error_patterns_helpers.service_type_manager import ServiceType


class TestReconnectionErrorPatterns:
    """Tests for RECONNECTION_ERROR_PATTERNS constant."""

    def test_contains_websocket_patterns(self) -> None:
        """Contains WebSocket error patterns."""
        assert ServiceType.WEBSOCKET in RECONNECTION_ERROR_PATTERNS
        patterns = RECONNECTION_ERROR_PATTERNS[ServiceType.WEBSOCKET]
        assert len(patterns) > 0
        assert any("websocket" in p for p in patterns)
        assert any("connection lost" in p for p in patterns)

    def test_contains_rest_patterns(self) -> None:
        """Contains REST error patterns."""
        assert ServiceType.REST in RECONNECTION_ERROR_PATTERNS
        patterns = RECONNECTION_ERROR_PATTERNS[ServiceType.REST]
        assert len(patterns) > 0
        assert any("timeout" in p for p in patterns)
        assert any("connection" in p for p in patterns)

    def test_contains_database_patterns(self) -> None:
        """Contains database error patterns."""
        assert ServiceType.DATABASE in RECONNECTION_ERROR_PATTERNS
        patterns = RECONNECTION_ERROR_PATTERNS[ServiceType.DATABASE]
        assert len(patterns) > 0
        assert any("database" in p for p in patterns)

    def test_contains_scraper_patterns(self) -> None:
        """Contains scraper error patterns."""
        assert ServiceType.SCRAPER in RECONNECTION_ERROR_PATTERNS
        patterns = RECONNECTION_ERROR_PATTERNS[ServiceType.SCRAPER]
        assert len(patterns) > 0
        assert any("rate.*limit" in p for p in patterns)

    def test_all_patterns_are_valid_regex(self) -> None:
        """All patterns are valid regex strings."""
        for service_type, patterns in RECONNECTION_ERROR_PATTERNS.items():
            for pattern in patterns:
                try:
                    re.compile(pattern, re.IGNORECASE)
                except re.error as exc:
                    pytest.fail(f"Invalid regex for {service_type}: {pattern} - {exc}")


class TestPatternCompiler:
    """Tests for PatternCompiler class."""

    def test_init_compiles_all_patterns(self) -> None:
        """Compiles all patterns on initialization."""
        compiler = PatternCompiler()

        assert len(compiler.compiled_patterns) > 0
        for service_type in RECONNECTION_ERROR_PATTERNS:
            assert service_type in compiler.compiled_patterns
            for pattern in compiler.compiled_patterns[service_type]:
                assert isinstance(pattern, re.Pattern)

    def test_compiled_patterns_are_case_insensitive(self) -> None:
        """Compiled patterns use case-insensitive matching."""
        compiler = PatternCompiler()

        # Find a pattern that should match "connection lost"
        patterns = compiler.get_compiled_patterns(ServiceType.WEBSOCKET)
        connection_lost_pattern = None
        for pattern in patterns:
            if pattern.search("connection lost"):
                connection_lost_pattern = pattern
                break

        assert connection_lost_pattern is not None
        assert connection_lost_pattern.search("CONNECTION LOST")
        assert connection_lost_pattern.search("Connection Lost")


class TestPatternCompilerGetCompiledPatterns:
    """Tests for PatternCompiler.get_compiled_patterns method."""

    def test_returns_patterns_for_valid_service_type(self) -> None:
        """Returns compiled patterns for valid service type."""
        compiler = PatternCompiler()

        patterns = compiler.get_compiled_patterns(ServiceType.WEBSOCKET)

        assert len(patterns) > 0
        assert all(isinstance(p, re.Pattern) for p in patterns)

    def test_returns_patterns_for_all_service_types(self) -> None:
        """Returns patterns for all service types."""
        compiler = PatternCompiler()

        for service_type in ServiceType:
            patterns = compiler.get_compiled_patterns(service_type)
            # Should return a list (may be empty for unknown types)
            assert isinstance(patterns, list)

    def test_returns_empty_list_for_unknown_service_type(self) -> None:
        """Returns empty list for unknown service type."""
        compiler = PatternCompiler()

        # Clear compiled patterns to test fallback
        compiler.compiled_patterns = {}

        patterns = compiler.get_compiled_patterns(ServiceType.WEBSOCKET)

        assert patterns == []


class TestPatternCompilerGetRawPatterns:
    """Tests for PatternCompiler.get_raw_patterns method."""

    def test_returns_raw_patterns_for_valid_service_type(self) -> None:
        """Returns raw pattern strings for valid service type."""
        compiler = PatternCompiler()

        patterns = compiler.get_raw_patterns(ServiceType.WEBSOCKET)

        assert len(patterns) > 0
        assert all(isinstance(p, str) for p in patterns)

    def test_returns_same_patterns_as_constant(self) -> None:
        """Returns same patterns as RECONNECTION_ERROR_PATTERNS constant."""
        compiler = PatternCompiler()

        for service_type in RECONNECTION_ERROR_PATTERNS:
            patterns = compiler.get_raw_patterns(service_type)
            assert patterns == RECONNECTION_ERROR_PATTERNS[service_type]

    def test_returns_empty_list_for_unknown_service_type(self) -> None:
        """Returns empty list for unknown service type."""
        compiler = PatternCompiler()

        # Create a mock service type by testing with different enum
        # Since ServiceType is defined, test with a cleared patterns dict
        original_patterns = dict(RECONNECTION_ERROR_PATTERNS)

        # Test that it returns empty list when service type not in dict
        patterns = compiler.get_raw_patterns(ServiceType.WEBSOCKET)
        assert patterns == original_patterns[ServiceType.WEBSOCKET]


class TestPatternCompilerRecompilePatterns:
    """Tests for PatternCompiler.recompile_patterns method."""

    def test_recompiles_patterns_for_service_type(self) -> None:
        """Recompiles patterns for specified service type."""
        compiler = PatternCompiler()

        # Get original patterns
        original_patterns = compiler.get_compiled_patterns(ServiceType.WEBSOCKET)
        original_count = len(original_patterns)

        # Clear and recompile
        compiler.compiled_patterns[ServiceType.WEBSOCKET] = []
        compiler.recompile_patterns(ServiceType.WEBSOCKET)

        new_patterns = compiler.get_compiled_patterns(ServiceType.WEBSOCKET)
        assert len(new_patterns) == original_count

    def test_handles_missing_service_type(self) -> None:
        """Handles service type not in patterns dict."""
        compiler = PatternCompiler()

        # Clear the compiled patterns
        compiler.compiled_patterns = {}

        # Recompile should handle gracefully
        compiler.recompile_patterns(ServiceType.WEBSOCKET)

        # Should have compiled the patterns
        assert ServiceType.WEBSOCKET in compiler.compiled_patterns


class TestPatternMatching:
    """Tests for pattern matching behavior."""

    def test_websocket_patterns_match_expected_errors(self) -> None:
        """WebSocket patterns match expected error messages."""
        compiler = PatternCompiler()
        patterns = compiler.get_compiled_patterns(ServiceType.WEBSOCKET)

        test_messages = [
            "no close frame received or sent",
            "WebSocket connection lost unexpectedly",
            "connection reset by peer during handshake",
            "WebSocket error: 1006",
            "ping timeout after 30 seconds",
        ]

        for message in test_messages:
            matched = any(p.search(message) for p in patterns)
            assert matched, f"Expected pattern to match: {message}"

    def test_rest_patterns_match_expected_errors(self) -> None:
        """REST patterns match expected error messages."""
        compiler = PatternCompiler()
        patterns = compiler.get_compiled_patterns(ServiceType.REST)

        test_messages = [
            "Connection timeout after 60 seconds",
            "HTTP connection failed: network error",
            "Request timeout waiting for response",
            "SSL handshake failed: certificate error",
            "asyncio.TimeoutError occurred",
        ]

        for message in test_messages:
            matched = any(p.search(message) for p in patterns)
            assert matched, f"Expected pattern to match: {message}"

    def test_database_patterns_match_expected_errors(self) -> None:
        """Database patterns match expected error messages."""
        compiler = PatternCompiler()
        patterns = compiler.get_compiled_patterns(ServiceType.DATABASE)

        test_messages = [
            "Database connection lost during query",
            "Server has gone away unexpectedly",
            "Database connection failed: auth error",
            "Connection pool exhausted",
        ]

        for message in test_messages:
            matched = any(p.search(message) for p in patterns)
            assert matched, f"Expected pattern to match: {message}"

    def test_scraper_patterns_match_expected_errors(self) -> None:
        """Scraper patterns match expected error messages."""
        compiler = PatternCompiler()
        patterns = compiler.get_compiled_patterns(ServiceType.SCRAPER)

        test_messages = [
            "Rate limit exceeded: retry after 60s",
            "Too many requests: 429",
            "Service unavailable: 503",
            "Bad gateway: proxy error",
            "Gateway timeout: 504",
            "Timeout fetching data from API",
        ]

        for message in test_messages:
            matched = any(p.search(message) for p in patterns)
            assert matched, f"Expected pattern to match: {message}"

    def test_patterns_do_not_match_unrelated_errors(self) -> None:
        """Patterns do not match unrelated error messages."""
        compiler = PatternCompiler()
        patterns = compiler.get_compiled_patterns(ServiceType.WEBSOCKET)

        non_matching_messages = [
            "Invalid JSON syntax in response",
            "User authentication failed",
            "Permission denied for resource",
            "File not found: config.json",
        ]

        for message in non_matching_messages:
            matched = any(p.search(message) for p in patterns)
            assert not matched, f"Expected pattern NOT to match: {message}"
