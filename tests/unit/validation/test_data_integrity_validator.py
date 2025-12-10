import math
from datetime import datetime, timezone

import numpy as np
import pytest

from common.validation import DataIntegrityError, DataIntegrityValidator
from tests.helpers.array_builders import literal_array

_CONST_NEG_2 = -2
_TEST_COUNT_2 = 2


def test_validate_numeric_value_accepts_valid_input():
    result = DataIntegrityValidator.validate_numeric_value("3.14", "pi")
    assert math.isclose(result, 3.14)


@pytest.mark.parametrize(
    "value, expected_message",
    [
        (None, "None value not allowed for number"),
        ("bad", "Cannot convert number to numeric value"),
        (float("nan"), "NaN value not allowed"),
        (float("inf"), "Infinite value not allowed"),
    ],
)
def test_validate_numeric_value_rejects_invalid_inputs(value, expected_message):
    with pytest.raises(DataIntegrityError) as exc:
        DataIntegrityValidator.validate_numeric_value(value, "number")

    assert expected_message in str(exc.value)


def test_validate_numeric_value_respects_zero_and_negative_constraints():
    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_numeric_value(0, "count", allow_zero=False)

    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_numeric_value(-1, "count", allow_negative=False)

    # Negative allowed when explicitly permitted
    assert (
        DataIntegrityValidator.validate_numeric_value(-2, "delta", allow_negative=True)
        == _CONST_NEG_2
    )


def test_validate_numeric_value_checks_bounds():
    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_numeric_value(3, "bounded", min_value=5)

    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_numeric_value(11, "bounded", max_value=10)


def test_validate_expiry_value_enforces_domain():
    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_expiry_value(0.0)

    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_expiry_value(20.0)

    assert DataIntegrityValidator.validate_expiry_value(0.5) == pytest.approx(0.5)


def test_validate_numpy_array_success_and_shape_checks():
    array = DataIntegrityValidator.validate_numpy_array([1, 2, 3], "numbers", min_length=3)
    assert np.array_equal(array, literal_array([1, 2, 3]))

    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_numpy_array([], "empty", allow_empty=False)

    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_numpy_array([1, 2], "shape", expected_shape=(3,))


def test_validate_numpy_array_detects_nan_and_inf():
    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_numpy_array([1, np.nan], "nan_array", allow_empty=True)

    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_numpy_array([1, np.inf], "inf_array", allow_empty=True)


def test_validate_json_data_parses_string(monkeypatch):
    parsed = DataIntegrityValidator.validate_json_data('{"key": "value"}')
    assert parsed == {"key": "value"}

    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_json_data("")

    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_json_data(123)


def test_validate_surface_prediction_result_success_and_failures():
    valid = DataIntegrityValidator.validate_surface_prediction_result(
        (0.1, -0.2, -0.3, 1.5, 0.7, 2.0)
    )
    assert valid == (0.1, -0.2, -0.3, 1.5, 0.7, 2.0)

    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_surface_prediction_result((1, 2, 3))

    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_surface_prediction_result(
            (0, 0, 0, 0, 0, -1), variable_name="surface"
        )


def test_validate_bid_ask_prices_detects_crossing():
    bid, ask = DataIntegrityValidator.validate_bid_ask_prices(1, 2)
    assert bid == 1
    assert ask == _TEST_COUNT_2

    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_bid_ask_prices(5, 1)


def test_validate_gp_surface_object_checks_methods():
    class DummySurface:
        def predict_three_surfaces(self):
            return None

    assert DataIntegrityValidator.validate_gp_surface_object(DummySurface()) is not None

    class IncompleteSurface:
        pass

    with pytest.raises(DataIntegrityError):
        DataIntegrityValidator.validate_gp_surface_object(IncompleteSurface())


def test_log_validation_success_emits_debug(caplog):
    caplog.set_level("DEBUG")
    DataIntegrityValidator.log_validation_success("field", 10)
    assert any("[DATA_VALIDATION]" in record.message for record in caplog.records)


def test_create_validation_summary(monkeypatch):
    timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr("common.time_utils.get_current_utc", lambda: timestamp)

    summary = DataIntegrityValidator.create_validation_summary(
        [("field", "value"), ("other", "x" * 60)]
    )

    assert "Timestamp: 2024-01-01T00:00:00+00:00" in summary
    assert "field" in summary
    assert "..." in summary
