import pytest

from common.status_reporter_helpers.formatters import (
    _build_message_components,
    build_opportunities_summary,
)


class TestSummaryBuilder:
    def test_build_opportunities_summary_none(self):
        assert build_opportunities_summary(0, 0, 0) == "📊 No trading opportunities found"

    def test_build_opportunities_summary_found_only(self):
        result = build_opportunities_summary(5, 0, 0)
        assert "Found 5 opportunities" in result
        assert "5 opportunities could not be traded" in result

    def test_build_opportunities_summary_found_executed(self):
        result = build_opportunities_summary(5, 2, 0)
        assert "Found 5 opportunities" in result
        assert "2 trades executed successfully" in result
        assert "3 opportunities could not be traded" in result

    def test_build_opportunities_summary_all_executed(self):
        result = build_opportunities_summary(5, 5, 0)
        assert "Found 5 opportunities" in result
        assert "5 trades executed successfully" in result
        assert "could not be traded" not in result

    def test_build_opportunities_summary_with_closed(self):
        result = build_opportunities_summary(5, 2, 3)
        assert "Found 5 opportunities" in result
        assert "2 trades executed successfully" in result
        assert "3 opportunities could not be traded" in result
        assert "3 markets closed for the day" in result

    def test_build_message_components_singular(self):
        components = _build_message_components(1, 1, 1)
        assert "Found 1 opportunity" in components
        assert "1 trade executed successfully" in components
        assert "1 market closed for the day" in components

    def test_build_message_components_untradeable_singular(self):
        components = _build_message_components(2, 1, 0)
        assert "1 opportunity could not be traded" in components

    def test_build_opportunities_summary_empty_components(self):
        assert build_opportunities_summary(0, 0, 0) == "📊 No trading opportunities found"

    def test_build_opportunities_summary_formatting(self):
        pass
