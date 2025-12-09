"""Tests for status_line helper."""

from unittest.mock import patch

from src.common.optimized_status_reporter_helpers.status_line import emit_status_line


@patch("src.common.optimized_status_reporter_helpers.status_line.output")
def test_emit_status_line_uses_output(mock_output):
    emit_status_line("hello")
    mock_output.assert_called_with("hello", headers=False, log=True, plain_log=True)


@patch("src.common.optimized_status_reporter_helpers.status_line.output")
def test_emit_status_line_defaults_to_blank(mock_output):
    emit_status_line()
    mock_output.assert_called_with("", headers=False, log=True, plain_log=True)
