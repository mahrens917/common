from datetime import datetime

import pytest

import src.common.user_display as user_display_module
from src.common.user_display import UserDisplay

_TEST_COUNT_2 = 2


def test_show_startup_prints_and_sets_timer(capsys):
    display = UserDisplay()

    display.show_startup(["BTC", "ETH"])

    out = capsys.readouterr().out
    assert "Starting Kalshi PDF Generator" in out
    assert "BTC, ETH" in out
    assert display.start_time is not None


def test_show_step_and_completion_messages(capsys):
    display = UserDisplay()

    display.show_step(1, "Load data", "from Deribit")
    display.show_step_complete(1, "Load data", "finished")

    out = capsys.readouterr().out
    assert "Step 1" in out
    assert "from Deribit" in out
    assert "Step 1 complete: finished" in out


def test_show_data_loading_totals(capsys):
    display = UserDisplay()

    display.show_data_loading("BTC", options_count=12, futures_count=5)

    out = capsys.readouterr().out
    assert "17 Deribit data points" in out
    assert "(12 options + 5 futures)" in out


def test_show_error_confidence_summary_handles_none(capsys):
    display = UserDisplay()

    display.show_error_confidence_summary(None, None)

    out = capsys.readouterr().out
    assert "Overall Average Error: N/A" in out
    assert "Overall Average Confidence: N/A" in out


def test_show_timing_summary_pass_status(capsys):
    display = UserDisplay()
    phases = [("fetch", 0.010), ("compute", 0.020)]

    display.show_timing_summary(phases, sum_seconds=0.030, total_seconds=0.030003)

    out = capsys.readouterr().out
    assert "EXECUTION TIMING SUMMARY" in out
    assert "⏱️  fetch" in out
    assert "PASSED" in out
    assert "gap:" in out


def test_show_timing_summary_fail_status(capsys):
    display = UserDisplay()
    phases = [("fetch", 0.005), ("compute", 0.010)]

    display.show_timing_summary(phases, sum_seconds=0.015, total_seconds=0.030)

    out = capsys.readouterr().out
    assert "⚠️" in out
    assert "FAILED" in out


def test_convenience_wrappers_delegate_to_global_instance(monkeypatch, capsys):
    custom_display = UserDisplay()
    monkeypatch.setattr(user_display_module, "_user_display", custom_display)

    custom_display.show_startup(["BTC"])  # warm up to set timer, not captured
    capsys.readouterr()  # clear any buffered output

    user_display_module.show_progress(2, "Process trades", "batch A")
    user_display_module.show_completion(2, "Process trades", "done")
    user_display_module.show_error("something went wrong")
    user_display_module.show_warning("check inputs")

    out = capsys.readouterr().out
    assert "Step 2" in out
    assert "done" in out
    assert "❌ something went wrong" in out
    assert "⚠️" in out
    assert custom_display.current_step == _TEST_COUNT_2


def test_get_user_display_returns_global_instance(monkeypatch):
    custom_display = UserDisplay()
    monkeypatch.setattr(user_display_module, "_user_display", custom_display)

    retrieved = user_display_module.get_user_display()

    assert retrieved is custom_display


def test_show_surface_quality_lists_values(capsys):
    display = UserDisplay()

    display.show_surface_quality("BTC", [0.92, 0.88], ["Short", "Long"])

    out = capsys.readouterr().out
    assert "R²=0.92 (Short)" in out
    assert "Overall surface R²=0.90" in out


def test_show_surface_quality_errors_on_missing_data():
    display = UserDisplay()

    with pytest.raises(ValueError):
        display.show_surface_quality("BTC", [], [])


def test_misc_display_helpers(capsys):
    display = UserDisplay()

    display.show_service_ready()
    display.show_kalshi_targets(5)
    display.show_probability_calculation("BTC", successful=7, total=10)
    display.show_market_updates(successful=3, total=4)
    display.show_completion("BTC", total_calculations=42, processing_time=1.23)

    out = capsys.readouterr().out
    assert "Service initialized" in out
    assert "Loaded 5 Kalshi target points" in out
    assert "Calculated 7/10 probabilities" in out
    assert "Updated 3/4 Kalshi markets" in out
    assert "42 probabilities calculated" in out


def test_show_total_time_no_output_when_not_started(capsys):
    display = UserDisplay()
    display.show_total_time()
    assert capsys.readouterr().out == ""


def test_show_total_time_after_start(capsys):
    display = UserDisplay()
    display.show_startup(["BTC"])
    capsys.readouterr()

    display.show_total_time()
    assert capsys.readouterr().out == ""
