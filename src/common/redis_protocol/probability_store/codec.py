from __future__ import annotations

"""Codec utilities for probability payloads."""

import math
from decimal import Decimal
from typing import Any, Dict, Tuple, Union

import orjson

from ..error_types import JSON_ERRORS
from .exceptions import ProbabilityStoreError


def decode_redis_key(raw_key: Any) -> str:
    """Decode Redis keys that may be stored as bytes."""
    if isinstance(raw_key, bytes):
        return raw_key.decode("utf-8")
    return str(raw_key)


def serialize_probability_payload(data: Dict[str, Any]) -> Tuple[str, bool]:
    """Serialise a probability payload to JSON while tracking confidence inclusion."""
    normalized: Dict[str, Any] = {}
    has_confidence = False
    for field_name, field_value in data.items():
        if isinstance(field_value, Decimal):
            normalized[field_name] = float(field_value)
        else:
            normalized[field_name] = field_value

    confidence_value = normalized.get("confidence")
    if confidence_value is not None:
        has_confidence = True
        if isinstance(confidence_value, float) and math.isnan(confidence_value):
            normalized["confidence"] = "NaN"

    try:
        value = orjson.dumps(normalized).decode()
    except JSON_ERRORS as exc:  # pragma: no cover - serialization guard
        raise ProbabilityStoreError(f"Failed to serialise probability payload: {data}") from exc

    if has_confidence and '"confidence":' not in value:
        raise ProbabilityStoreError("Confidence value was dropped during serialization")

    return value, has_confidence


def decode_probability_hash(
    raw_data: Dict[Any, Any], *, key_str: str, log_nan: bool, logger_fn
) -> Dict[str, Union[str, float]]:
    """Convert Redis hash payload into python primitives."""
    processed: Dict[str, Union[str, float]] = {}
    for field, value in raw_data.items():
        field_name = decode_redis_key(field)
        value_text = decode_redis_key(value)

        if value_text == "NaN":
            processed[field_name] = "NaN"
            if log_nan:
                logger_fn("Retrieved NaN value for field %s in key %s", field_name, key_str)
            continue

        try:
            processed[field_name] = float(value_text)
        except ValueError:
            processed[field_name] = value_text

    return processed


__all__ = [
    "decode_redis_key",
    "serialize_probability_payload",
    "decode_probability_hash",
]
