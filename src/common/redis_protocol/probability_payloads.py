from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

NULLABLE_OPTIONAL_FIELDS = {"range_low", "range_high"}
EXCLUDED_FIELDS = {"strike_type", "floor_strike", "cap_strike", "market_ticker"}


@dataclass(frozen=True)
class ProbabilityFieldDiagnostics:
    """Metadata describing which optional fields were serialised for logging."""

    error_value: Optional[Any]
    stored_error: bool
    confidence_value: Optional[Any]
    stored_confidence: bool


@dataclass(frozen=True)
class ProbabilityRecord:
    """Serialised representation ready for Redis storage."""

    key: str
    fields: Dict[str, str]
    event_ticker: Optional[str]
    diagnostics: ProbabilityFieldDiagnostics


def build_probability_record(
    currency: str,
    expiry: str,
    strike_value: Any,
    payload: Dict[str, Any],
    *,
    default_missing_event_ticker: bool = True,
) -> ProbabilityRecord:
    """
    Construct the Redis key and payload mapping for a probability entry.

    Args:
        currency: Normalised currency symbol (already upper-cased).
        expiry: Expiry timestamp string.
        strike_value: Raw strike value from the payload.
        payload: Probability payload containing optional metadata fields.
        default_missing_event_ticker: When True, store ``event_ticker='null'`` if absent.
    """
    strike_type = payload.get("strike_type")
    if not strike_type:
        strike_type = "unknown"
    normalised_strike = normalise_strike_value(strike_value)
    key = f"probabilities:{currency}:{expiry}:{strike_type}:{normalised_strike}"

    fields, diagnostics = serialize_probability_payload(payload, default_missing_event_ticker=default_missing_event_ticker)

    raw_event_ticker = fields.get("event_ticker")
    event_ticker = raw_event_ticker if raw_event_ticker and raw_event_ticker != "null" else None

    return ProbabilityRecord(
        key=key,
        fields=fields,
        event_ticker=event_ticker,
        diagnostics=diagnostics,
    )


def normalise_strike_value(strike_value: Any) -> str:
    """Round numeric strikes to the nearest integer; reject non-numeric inputs."""
    try:
        numeric_value = float(strike_value)
    except (TypeError, ValueError) as exc:  # policy_guard: allow-silent-handler
        raise TypeError(f"Strike value {strike_value!r} must be numeric") from exc

    if math.isnan(numeric_value) or math.isinf(numeric_value):
        raise TypeError(f"Strike value {strike_value!r} must be finite")

    return str(int(round(numeric_value)))


def serialize_probability_payload(
    payload: Dict[str, Any], *, default_missing_event_ticker: bool = True
) -> Tuple[Dict[str, str], ProbabilityFieldDiagnostics]:
    """
    Convert an in-memory probability payload into Redis-ready string values.

    The serializer preserves NaN markers, normalises Decimal values, and only
    includes optional fields when they are present (or explicitly requested).
    """
    mapping: Dict[str, str] = {}
    diagnostics = _initialize_diagnostics(payload)

    _serialize_nullable_fields(payload, mapping)
    _serialize_event_ticker(payload, mapping, default_missing_event_ticker)
    diagnostics = _serialize_remaining_fields(payload, mapping, diagnostics)

    return mapping, diagnostics


def _initialize_diagnostics(payload: Dict[str, Any]) -> ProbabilityFieldDiagnostics:
    """Initialize diagnostics with error and confidence values"""
    return ProbabilityFieldDiagnostics(
        error_value=payload.get("error"),
        stored_error=False,
        confidence_value=payload.get("confidence"),
        stored_confidence=False,
    )


def _serialize_nullable_fields(payload: Dict[str, Any], mapping: Dict[str, str]) -> None:
    """Serialize nullable optional fields (range_low, range_high)"""
    for field_name in NULLABLE_OPTIONAL_FIELDS:
        if field_name in payload:
            mapping[field_name] = _serialize_nullable(payload.get(field_name))


def _serialize_event_ticker(payload: Dict[str, Any], mapping: Dict[str, str], default_missing_event_ticker: bool) -> None:
    """Serialize event_ticker with optional default handling"""
    event_ticker_value = payload.get("event_ticker")
    if default_missing_event_ticker:
        if event_ticker_value is None or str(event_ticker_value).strip() == "":
            mapping["event_ticker"] = "null"
        else:
            mapping["event_ticker"] = _serialize_value(event_ticker_value)
    elif event_ticker_value is not None:
        mapping["event_ticker"] = _serialize_value(event_ticker_value)


def _serialize_remaining_fields(
    payload: Dict[str, Any],
    mapping: Dict[str, str],
    diagnostics: ProbabilityFieldDiagnostics,
) -> ProbabilityFieldDiagnostics:
    """Serialize remaining payload fields and update diagnostics"""
    for field_name, value in payload.items():
        if _should_skip_field(field_name):
            continue

        serialized = _serialize_optional(value)
        if serialized is None:
            continue

        mapping[field_name] = serialized
        diagnostics = _update_diagnostics_for_field(field_name, diagnostics)

    return diagnostics


def _should_skip_field(field_name: str) -> bool:
    """Check if field should be skipped during serialization"""
    return field_name in EXCLUDED_FIELDS or field_name in NULLABLE_OPTIONAL_FIELDS or field_name == "event_ticker"


def _update_diagnostics_for_field(field_name: str, diagnostics: ProbabilityFieldDiagnostics) -> ProbabilityFieldDiagnostics:
    """Update diagnostics when error or confidence fields are stored"""
    if field_name == "error":
        return ProbabilityFieldDiagnostics(
            error_value=diagnostics.error_value,
            stored_error=True,
            confidence_value=diagnostics.confidence_value,
            stored_confidence=diagnostics.stored_confidence,
        )
    if field_name == "confidence":
        return ProbabilityFieldDiagnostics(
            error_value=diagnostics.error_value,
            stored_error=diagnostics.stored_error,
            confidence_value=diagnostics.confidence_value,
            stored_confidence=True,
        )
    return diagnostics


def _serialize_optional(value: Any) -> Optional[str]:
    if value is None:
        return None
    return _serialize_value(value)


def _serialize_nullable(value: Any) -> str:
    if value is None:
        _none_guard_value = "null"
        return _none_guard_value
    return _serialize_value(value)


def _serialize_value(value: Any) -> str:
    if isinstance(value, Decimal):
        formatted = format(value, "f").rstrip("0").rstrip(".")
        if not formatted:
            return "0"
        return formatted
    if isinstance(value, float) and math.isnan(value):
        return "nan"
    return str(value)


__all__ = [
    "ProbabilityFieldDiagnostics",
    "ProbabilityRecord",
    "build_probability_record",
    "normalise_strike_value",
    "serialize_probability_payload",
]
