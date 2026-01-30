import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

DEFAULT_MAX_TEMP_THRESHOLD_F = 60
DEFAULT_MAX_TEMP_RESULT_F = 72

from common.exceptions import DataError
from common.midnight_reset_service_helpers.daily_checker import DailyChecker
from common.midnight_reset_service_helpers.delegator import MidnightResetDelegator
from common.midnight_reset_service_helpers.factory import create_midnight_reset_service
from common.midnight_reset_service_helpers.field_reset_applicator import FieldResetApplicator
from common.midnight_reset_service_helpers.max_temp_processor import (
    MaxTempProcessingConfig,
    MaxTempProcessor,
)
from common.midnight_reset_service_helpers.max_temp_processor_helpers import (
    add_observations_to_state,
    extract_result_for_trading,
    initialize_or_restore_daily_state,
)
from common.midnight_reset_service_helpers.reset_evaluator import ResetEvaluator
from common.midnight_reset_service_helpers.timestamp_mapper import TimestampMapper

pytestmark = pytest.mark.unit


def test_daily_checker_detects_new_day(monkeypatch):
    checker = DailyChecker()
    previous = datetime(2024, 1, 1, 23, 0, tzinfo=timezone.utc)
    now = previous + timedelta(hours=2)
    monkeypatch.setattr(
        "common.midnight_reset_service_helpers.daily_checker.calculate_local_midnight_utc",
        lambda lat, lon, ts: previous + timedelta(hours=1),
    )

    assert checker.is_new_local_day(10.0, 20.0, previous, now) is True

    # Before the midnight boundary we should not reset
    monkeypatch.setattr(
        "common.midnight_reset_service_helpers.daily_checker.calculate_local_midnight_utc",
        lambda lat, lon, ts: previous + timedelta(hours=3),
    )
    assert checker.is_new_local_day(10.0, 20.0, previous, now) is False


def test_reset_evaluator_timestamp_paths(monkeypatch):
    mapper = TimestampMapper()
    daily_checker = SimpleNamespace(is_new_local_day=lambda *args, **kwargs: False)
    evaluator = ResetEvaluator(daily_checker, mapper)

    assert evaluator.should_reset_field("unknown", 0, 0, {"last_updated": "2024-01-01T00:00:00Z"}) is False
    assert evaluator.should_reset_field("max_temp_f", 0, 0, {}) is True
    assert evaluator.should_reset_field("max_temp_f", 0, 0, {"missing": "field"}) is True
    assert evaluator.should_reset_field("max_temp_f", 0, 0, {"max_start_time": None}) is True

    previous = {"max_start_time": "2024-01-01T00:00:00Z"}
    assert evaluator.should_reset_field("max_temp_f", 0, 0, previous) is False

    daily_checker.is_new_local_day = lambda *args, **kwargs: True
    assert evaluator.should_reset_field("max_temp_f", 0, 0, previous) is True


def test_field_reset_applicator_resets_and_reuses_previous(monkeypatch):
    class StubEvaluator:
        DAILY_RESET_FIELDS = {"t_bid"}

        def __init__(self, should_reset: bool):
            self._should_reset = should_reset

        def should_reset_field(self, *args, **kwargs):
            return self._should_reset

    applicator = FieldResetApplicator(StubEvaluator(True))
    value, was_reset = applicator.apply_field_resets("t_bid", "0.55", {"last_updated": "2024-01-01T00:00:00Z"}, 0, 0)
    assert was_reset is True and value is None

    applicator = FieldResetApplicator(StubEvaluator(False))
    value, was_reset = applicator.apply_field_resets("t_bid", None, {"t_bid": "0.60", "last_updated": "2024-01-01T00:00:00Z"}, 0, 0)
    assert was_reset is False and value == "0.60"

    value, was_reset = applicator.apply_field_resets(
        "max_temp_f",
        DEFAULT_MAX_TEMP_RESULT_F,
        {"max_temp_f": 70, "max_start_time": "2024-01-01T00:00:00Z"},
        0,
        0,
    )
    assert was_reset is False and value == DEFAULT_MAX_TEMP_RESULT_F


def test_midnight_reset_delegator_routes_calls():
    calls = []

    class StubChecker:
        def is_new_local_day(self, *args, **kwargs):
            calls.append("check")
            return True

    class StubMapper:
        def get_timestamp_field_for_reset_field(self, name: str):
            return f"{name}_ts"

    class StubEvaluator:
        def should_reset_field(self, *args, **kwargs):
            calls.append("reset")
            return False

    class StubApplicator:
        def apply_field_resets(self, *args, **kwargs):
            calls.append("apply")
            return "value", True

    class StubMaxTemp:
        def apply_confidence_based_max_temp_logic(self, config):
            calls.append(("max_temp", config.current_temp_c))
            return ("temp", "ts", "HIGH", None)

    delegator = MidnightResetDelegator(StubChecker(), StubMapper(), StubEvaluator(), StubApplicator(), StubMaxTemp())

    assert delegator.is_new_local_day(0, 0, datetime.now(timezone.utc)) is True
    assert delegator.should_reset_field("field", 0, 0, {}) is False
    assert delegator.apply_field_resets("field", 1, {}, 0, 0) == ("value", True)
    assert (
        delegator.apply_confidence_based_max_temp_logic(
            MaxTempProcessingConfig(
                current_temp_c=1.0,
                previous_data={},
                latitude=0,
                longitude=0,
                current_timestamp_str="ts",
            )
        )[0]
        == "temp"
    )
    assert calls == ["check", "reset", "apply", ("max_temp", 1.0)]


def test_factory_creates_wired_service(monkeypatch):
    midnight_service = create_midnight_reset_service()
    previous = datetime(2024, 1, 1, 23, 0, tzinfo=timezone.utc)
    current = previous + timedelta(hours=2)

    monkeypatch.setattr(
        "common.midnight_reset_service_helpers.daily_checker.calculate_local_midnight_utc",
        lambda lat, lon, ts: previous + timedelta(hours=1),
    )

    assert midnight_service.is_new_local_day(0, 0, previous, current) is True


def test_max_temp_processor_handles_reset_and_restore(monkeypatch):
    reset_evaluator = SimpleNamespace(should_reset_field=lambda *args, **kwargs: False)
    processor = MaxTempProcessor(reset_evaluator)
    base_time = datetime(2024, 1, 2, 6, 0, tzinfo=timezone.utc)
    previous_state = {"daily_max_state": json.dumps({"max_temp_c": 10, "timestamp": None})}

    config = MaxTempProcessingConfig(
        current_temp_c=19.0,
        previous_data=previous_state,
        latitude=0,
        longitude=0,
        current_timestamp_str=base_time.isoformat(),
        current_timestamp=base_time,
        six_hour_max_c=12,
        should_reset_override=False,
    )

    max_temp_f, start_time, confidence, state = processor.apply_confidence_based_max_temp_logic(config)
    assert start_time == base_time.isoformat()
    assert confidence in {"HIGH", "MEDIUM"}
    assert max_temp_f > DEFAULT_MAX_TEMP_THRESHOLD_F

    reset_evaluator.should_reset_field = lambda *args, **kwargs: True
    config_reset = MaxTempProcessingConfig(
        current_temp_c=22.0,
        previous_data=previous_state,
        latitude=0,
        longitude=0,
        current_timestamp_str=base_time.isoformat(),
        current_timestamp=base_time,
        six_hour_max_c=12,
        should_reset_override=True,
    )
    result = processor.apply_confidence_based_max_temp_logic(config_reset)
    assert result[2] in {"HIGH", "MEDIUM"}


def test_max_temp_processor_raises_on_corrupted_state():
    reset_evaluator = SimpleNamespace(should_reset_field=lambda *args, **kwargs: False)
    processor = MaxTempProcessor(reset_evaluator)
    config = MaxTempProcessingConfig(
        current_temp_c=20.0,
        previous_data={"daily_max_state": "{bad json"},
        latitude=0,
        longitude=0,
        current_timestamp_str="2024-01-02T06:00:00Z",
        current_timestamp=datetime(2024, 1, 2, 6, 0, tzinfo=timezone.utc),
        should_reset_override=False,
    )

    with pytest.raises(ValueError):
        processor.apply_confidence_based_max_temp_logic(config)


def test_max_temp_processor_helpers_initialize_and_extract(monkeypatch):
    loaded = {}

    class StubPersistence:
        def load_from_state_dict(self, state):
            loaded["state"] = state

    class StubDailyState:
        def __init__(self):
            self.persistence = StubPersistence()
            self.hourly = []
            self.window = []
            self.result = SimpleNamespace(max_temp_f=DEFAULT_MAX_TEMP_RESULT_F, confidence="HIGH", source="hourly")

        def add_hourly_observation(self, temp_c, timestamp):
            self.hourly.append((temp_c, timestamp))

        def add_6h_maximum(self, max_c, timestamp):
            self.window.append((max_c, timestamp))

        def get_daily_max_result(self):
            return self.result

    stub_state = StubDailyState()
    monkeypatch.setattr(
        "common.daily_max_state.create_daily_max_state",
        lambda: stub_state,
    )

    state = initialize_or_restore_daily_state(False, {"daily_max_state": '{"a": 1}'})
    assert loaded["state"] == {"a": 1}
    assert state is stub_state

    reset_state = initialize_or_restore_daily_state(True, {})
    assert reset_state is stub_state

    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    add_observations_to_state(stub_state, 20.0, now, 24)
    assert stub_state.hourly and stub_state.window

    max_temp_f, start_time, confidence = extract_result_for_trading(stub_state, "ts")
    assert max_temp_f == DEFAULT_MAX_TEMP_RESULT_F
    assert start_time == "ts"
    assert confidence == "HIGH"

    stub_state.result = None
    with pytest.raises(DataError):
        extract_result_for_trading(stub_state, "ts")
