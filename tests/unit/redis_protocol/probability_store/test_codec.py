"""Unit tests for probability_store codec module."""

from __future__ import annotations

import math

import pytest

from common.redis_protocol.probability_store.codec import (
    decode_probability_hash,
    decode_redis_key,
    serialize_probability_payload,
)
from common.redis_protocol.probability_store.exceptions import ProbabilityStoreError


class TestDecodeRedisKey:
    """Tests for decode_redis_key."""

    def test_decodes_bytes(self) -> None:
        assert decode_redis_key(b"hello") == "hello"

    def test_passes_through_string(self) -> None:
        assert decode_redis_key("hello") == "hello"

    def test_converts_other_types(self) -> None:
        assert decode_redis_key(123) == "123"


class TestSerializeProbabilityPayload:
    """Tests for serialize_probability_payload."""

    def test_basic_serialization(self) -> None:
        data = {"probability": 0.5, "event_type": "btc_above_50k"}
        value, has_confidence = serialize_probability_payload(data)
        assert isinstance(value, str)
        assert has_confidence is False

    def test_with_confidence(self) -> None:
        data = {"probability": 0.7, "confidence": 0.9}
        value, has_confidence = serialize_probability_payload(data)
        assert has_confidence is True
        assert '"confidence":' in value

    def test_nan_confidence_serialized(self) -> None:
        data = {"probability": 0.5, "confidence": float("nan")}
        value, has_confidence = serialize_probability_payload(data)
        assert has_confidence is True
        assert "NaN" in value

    def test_decimal_converted_to_float(self) -> None:
        from decimal import Decimal

        data = {"probability": Decimal("0.5")}
        value, has_confidence = serialize_probability_payload(data)
        assert "0.5" in value

    def test_raises_on_unserializable(self) -> None:
        data = {"probability": object()}
        with pytest.raises(ProbabilityStoreError, match="Failed to serialise"):
            serialize_probability_payload(data)


class TestDecodeProbabilityHash:
    """Tests for decode_probability_hash."""

    def test_decodes_float_values(self) -> None:
        raw = {b"probability": b"0.75"}
        result = decode_probability_hash(raw, key_str="k1", log_nan=False, logger_fn=lambda *a: None)
        assert result["probability"] == pytest.approx(0.75)

    def test_decodes_nan_value(self) -> None:
        raw = {b"confidence": b"NaN"}
        result = decode_probability_hash(raw, key_str="k1", log_nan=False, logger_fn=lambda *a: None)
        assert result["confidence"] == "NaN"

    def test_logs_nan_when_requested(self) -> None:
        logged = []
        raw = {b"confidence": b"NaN"}
        decode_probability_hash(raw, key_str="k1", log_nan=True, logger_fn=lambda *a: logged.append(a))
        assert len(logged) == 1

    def test_non_float_string_kept_as_string(self) -> None:
        raw = {b"event_type": b"btc_above_50k"}
        result = decode_probability_hash(raw, key_str="k1", log_nan=False, logger_fn=lambda *a: None)
        assert result["event_type"] == "btc_above_50k"

    def test_string_keys(self) -> None:
        raw = {"probability": "0.5"}
        result = decode_probability_hash(raw, key_str="k1", log_nan=False, logger_fn=lambda *a: None)
        assert result["probability"] == pytest.approx(0.5)
