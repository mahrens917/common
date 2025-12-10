import builtins
from datetime import datetime, timezone

import pytest

from common.daily_max_state import DailyMaxState, MetarConfigLoadError, cli_temp_f

_CONST_100 = 100
_CONST_32 = 32
_CONST_72 = 72
_VAL_0_1 = 0.1


def test_cli_temp_f_valid():
    assert cli_temp_f(0.4) == _CONST_32
    assert cli_temp_f(37.8) == _CONST_100


def test_cli_temp_f_none_raises():
    with pytest.raises(ValueError):
        cli_temp_f(None)


def test_daily_state_updates_with_hourly_and_6h(monkeypatch):
    def stub_config(self):
        return {"6h_max": {"safety_margin_celsius": 0.25}}

    monkeypatch.setattr(DailyMaxState, "_load_metar_config", stub_config)

    state = DailyMaxState()
    hourly_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    six_hour_time = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)

    state.add_hourly_observation(20.4, hourly_time)
    result = state.get_daily_max_result()
    assert result is not None
    assert result.confidence == "HIGH"
    assert result.precision_c == _VAL_0_1
    assert result.source == "hourly"
    assert result.timestamp == hourly_time
    assert state.get_hourly_only_max_f() == cli_temp_f(20.4)

    state.add_6h_maximum(22, six_hour_time)
    result = state.get_daily_max_result()
    assert result is not None
    # 22°C with 0.25°C safety margin becomes 21.75°C → 72°F
    assert result.max_temp_f == _CONST_72
    assert result.confidence == "MEDIUM"
    assert result.precision_c == 1.0
    assert result.source == "6h"

    conservative = state.get_adjusted_temp_for_rule("conservative")
    aggressive = state.get_adjusted_temp_for_rule("aggressive")
    assert conservative > aggressive

    with pytest.raises(ValueError):
        state.get_adjusted_temp_for_rule("unknown")


def test_state_round_trip(monkeypatch):
    def stub_config(self):
        return {}

    monkeypatch.setattr(DailyMaxState, "_load_metar_config", stub_config)

    original = DailyMaxState()
    timestamp = datetime(2024, 1, 2, 9, 30, tzinfo=timezone.utc)
    original.add_hourly_observation(15.6, timestamp)
    state_dict = original.get_state_dict()

    restored = DailyMaxState()
    restored.load_from_state_dict(state_dict)

    assert restored.max_temp_c == pytest.approx(original.max_temp_c)
    assert restored.precision == original.precision
    assert restored.source == original.source
    assert restored.timestamp == original.timestamp
    assert restored.get_hourly_only_max_f() == original.get_hourly_only_max_f()


def test_daily_max_result_without_data(monkeypatch):
    monkeypatch.setattr(
        DailyMaxState,
        "_load_metar_config",
        lambda self: {},
    )
    state = DailyMaxState()

    assert state.get_daily_max_result() is None


def test_reset_for_new_day_clears_state(monkeypatch):
    def stub_config(self):
        return {"6h_max": {"safety_margin_celsius": 0.1}}

    monkeypatch.setattr(DailyMaxState, "_load_metar_config", stub_config)

    state = DailyMaxState()
    timestamp = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    state.add_hourly_observation(19.2, timestamp)
    state.add_6h_maximum(25, timestamp)

    state.reset_for_new_day()

    assert state.get_daily_max_result() is None
    assert state.get_hourly_only_max_f() is None
    assert state.max_temp_c == float("-inf")
    assert state.hourly_max_temp_c == float("-inf")


def test_load_metar_config_missing_file(monkeypatch):
    def failing_open(*args, **kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr("builtins.open", failing_open)

    with pytest.raises(MetarConfigLoadError):
        DailyMaxState()
