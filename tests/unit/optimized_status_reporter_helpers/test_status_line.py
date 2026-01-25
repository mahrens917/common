"""Tests for status_line helper."""

from common.optimized_status_reporter_helpers.status_line import emit_status_line


def test_emit_status_line_is_noop():
    """emit_status_line is a no-op and should not raise."""
    emit_status_line("hello")


def test_emit_status_line_defaults_to_blank():
    """emit_status_line accepts no arguments and should not raise."""
    emit_status_line()
