from __future__ import annotations

import math
from decimal import Decimal

import pytest

from common.redis_protocol.probability_payloads import (
    ProbabilityRecord,
    build_probability_record,
    normalise_strike_value,
    serialize_probability_payload,
)


def test_build_probability_record_serializes_fields():
    record = build_probability_record(
        "BTC",
        "2025-03-01T00:00:00Z",
        "12345.6",
        {
            "strike_type": "greater",
            "probability": Decimal("0.4200"),
            "error": math.nan,
            "confidence": Decimal("0.7500"),
            "range_low": None,
            "event_ticker": "BTC-FOO",
        },
    )

    assert isinstance(record, ProbabilityRecord)
    assert record.key == "probabilities:BTC:2025-03-01T00:00:00Z:greater:12346"
    assert record.fields == {
        "range_low": "null",
        "event_ticker": "BTC-FOO",
        "probability": "0.42",
        "error": "nan",
        "confidence": "0.75",
    }
    assert record.event_ticker == "BTC-FOO"
    assert record.diagnostics.stored_error is True
    assert record.diagnostics.stored_confidence is True


def test_build_probability_record_without_default_event_ticker():
    record = build_probability_record(
        "ETH",
        "2025-04-01",
        100,
        {"strike_type": "less", "probability": 0.3},
        default_missing_event_ticker=False,
    )

    assert record.key == "probabilities:ETH:2025-04-01:less:100"
    assert "event_ticker" not in record.fields
    assert record.event_ticker is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("123.4", "123"),
        (123.6, "124"),
    ],
)
def test_normalise_strike_value_handles_inputs(value, expected):
    assert normalise_strike_value(value) == expected


@pytest.mark.parametrize("value", [">9000", "nan"])
def test_normalise_strike_value_rejects_invalid_inputs(value):
    with pytest.raises(TypeError):
        normalise_strike_value(value)


def test_serialize_probability_payload_defaults_missing_event_ticker():
    mapping, diagnostics = serialize_probability_payload(
        {"probability": 0.5}, default_missing_event_ticker=True
    )

    assert mapping["event_ticker"] == "null"
    assert mapping["probability"] == "0.5"
    assert diagnostics.stored_error is False


def test_serialize_probability_payload_serializes_event_ticker():
    mapping, diagnostics = serialize_probability_payload(
        {"probability": 0.5, "error": None, "strike_type": "greater", "event_ticker": "EVT-1"}
    )

    assert mapping == {"event_ticker": "EVT-1", "probability": "0.5"}
    assert diagnostics.stored_error is False
    assert diagnostics.error_value is None
