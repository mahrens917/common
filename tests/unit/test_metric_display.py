from common.user_display_helpers.metric_display import format_timing_summary


def test_timing_summary_allows_small_gap_with_dynamic_tolerance():
    # Use end-to-end runtime large enough to engage dynamic tolerance
    summary = format_timing_summary([("Phase A", 9.1)], sum_seconds=9.1, total_seconds=9.112)
    assert "PASSED" in summary
    assert "tolerance" in summary


def test_timing_summary_injects_overhead_for_large_positive_gap():
    summary = format_timing_summary([("Phase A", 0.5)], sum_seconds=0.5, total_seconds=0.7)
    assert "Pipeline Overhead" in summary
    assert "PASSED" in summary


def test_timing_summary_flags_negative_gap():
    summary = format_timing_summary([("Phase A", 0.5)], sum_seconds=0.5, total_seconds=0.1)
    assert "FAILED" in summary
