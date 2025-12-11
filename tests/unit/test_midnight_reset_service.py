import json
from datetime import datetime, timedelta, timezone

import pytest

from common.daily_max_state import DailyMaxState
from common.midnight_reset_service import MidnightResetService

_CONST_68 = 68
_CONST_72 = 72
_CONST_77 = 77
_VAL_25_0 = 25.0


@pytest.fixture
def service():
    return MidnightResetService()


def test_is_new_local_day_triggers(monkeypatch, service):
    previous = datetime(2024, 1, 1, 22, 0, tzinfo=timezone.utc)
    current = previous + timedelta(hours=5)

    monkeypatch.setattr(
        "common.time_utils.get_current_utc",
        lambda: current,
    )
    monkeypatch.setattr(
        "common.midnight_reset_service.calculate_local_midnight_utc",
        lambda lat, lon, ts: previous + timedelta(hours=3),
    )

    assert service.is_new_local_day(30.0, -97.0, previous, current) is True


def test_should_reset_field_first_run(service):
    assert service.should_reset_field("max_temp_f", 30.0, -97.0, {}) is True
    assert service.should_reset_field("unknown", 30.0, -97.0, {}) is False


def test_apply_field_resets(monkeypatch, service):
    previous_timestamp = datetime(2024, 1, 1, 21, 0, tzinfo=timezone.utc)
    current_time = previous_timestamp + timedelta(hours=2)

    monkeypatch.setattr(
        "common.midnight_reset_service.calculate_local_midnight_utc",
        lambda lat, lon, ts: previous_timestamp + timedelta(hours=6),
    )
    monkeypatch.setattr(
        "common.time_utils.get_current_utc",
        lambda: current_time,
    )

    previous_data = {"max_start_time": previous_timestamp.isoformat()}
    value, was_reset = service.apply_field_resets("max_temp_f", 72, previous_data, 30.0, -97.0, current_time)

    assert was_reset is False
    assert value == _CONST_72


def test_apply_confidence_based_max_temp_logic(monkeypatch, service):
    current_time = datetime(2024, 1, 2, 6, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("common.time_utils.get_current_utc", lambda: current_time)
    monkeypatch.setattr(
        "common.midnight_reset_service.calculate_local_midnight_utc",
        lambda lat, lon, ts: ts.replace(hour=5),
    )

    max_temp_f, start_time, confidence, daily_state = service.apply_confidence_based_max_temp_logic(
        current_temp_c=20.2,
        previous_data={},
        latitude=30.0,
        longitude=-97.0,
        current_timestamp_str=current_time.isoformat(),
        current_timestamp=current_time,
        six_hour_max_c=24,
    )

    assert max_temp_f >= _CONST_68
    assert start_time == current_time.isoformat()
    assert confidence in {"HIGH", "MEDIUM"}
    state_dict = daily_state.get_state_dict()
    json.dumps(state_dict)  # Ensure serializable


def test_apply_field_resets_clears_opt_in_fields(monkeypatch, service):
    previous_timestamp = datetime(2024, 1, 1, 21, 0, tzinfo=timezone.utc)
    current_time = previous_timestamp + timedelta(hours=4)

    monkeypatch.setattr(
        "common.midnight_reset_service.calculate_local_midnight_utc",
        lambda lat, lon, ts: previous_timestamp + timedelta(hours=1),
    )
    previous_data = {"last_updated": previous_timestamp.isoformat()}

    value, was_reset = service.apply_field_resets("t_yes_bid", "0.55", previous_data, 30.0, -97.0, current_time)

    assert was_reset is True
    assert value is None


def test_should_reset_field_handles_invalid_timestamp(service):
    previous_data = {"max_start_time": "not-a-valid-timestamp"}
    assert service.should_reset_field("max_temp_f", 30.0, -97.0, previous_data) is True


def test_apply_confidence_based_max_temp_logic_restores_previous_state(monkeypatch, service):
    base_time = datetime(2024, 1, 2, 6, 0, tzinfo=timezone.utc)
    state = DailyMaxState()
    state.add_hourly_observation(25.0, base_time)
    state_json = json.dumps(state.get_state_dict())

    monkeypatch.setattr(service, "should_reset_field", lambda *args, **kwargs: False)

    current_iso = (base_time + timedelta(hours=1)).isoformat()

    max_temp_f, start_time, confidence, daily_state = service.apply_confidence_based_max_temp_logic(
        current_temp_c=26.3,
        previous_data={"daily_max_state": state_json, "max_start_time": base_time.isoformat()},
        latitude=30.0,
        longitude=-97.0,
        current_timestamp_str=current_iso,
        current_timestamp=base_time + timedelta(hours=1),
        six_hour_max_c=None,
    )

    assert max_temp_f >= _CONST_77  # 26.3°C -> ~79°F with rounding
    assert confidence in {"HIGH", "MEDIUM"}
    assert daily_state.hourly_max_temp_c >= _VAL_25_0
    assert start_time == current_iso


def test_apply_confidence_based_max_temp_logic_raises_on_corrupted_state(monkeypatch, service):
    monkeypatch.setattr(service, "should_reset_field", lambda *args, **kwargs: False)

    with pytest.raises(ValueError):
        service.apply_confidence_based_max_temp_logic(
            current_temp_c=19.0,
            previous_data={"daily_max_state": "{bad json"},
            latitude=30.0,
            longitude=-97.0,
            current_timestamp_str="2024-01-02T06:00:00Z",
            current_timestamp=datetime(2024, 1, 2, 6, 0, tzinfo=timezone.utc),
        )
