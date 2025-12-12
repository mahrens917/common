from __future__ import annotations

"""Shared helpers for decoding Redis payloads.

The codebase previously scattered lightweight conversions (bytes→str decoding,
string-to-float coercion, etc.) across individual Redis stores. Centralising the
helpers keeps schema handling consistent and makes it easier to evolve payload
formats without hunting for bespoke parsing logic.
"""

from typing import Any, Iterable, Mapping

from common.exceptions import DataError


class FloatCoercionError(ValueError, DataError):
    """Raised when a value cannot be coerced into a float."""


__all__ = [
    "decode_redis_value",
    "decode_redis_hash",
    "coerce_float",
]


def decode_redis_value(value: Any) -> Any:
    """Normalise a Redis value into its Python representation.

    Redis returns ``bytes`` for most read operations. Callers that expect plain
    strings can run incoming values through this helper before additional
    parsing. Non-bytes values are returned untouched so integers/floats survive
    round-trips.
    """

    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def decode_redis_hash(raw_items: Mapping[Any, Any]) -> dict[str, Any]:
    """Decode a Redis hash response into a ``dict`` with string keys.

    Args:
        raw_items: Mapping returned by ``hgetall``/``hget`` pipelines.

    Returns:
        Dictionary with ``str`` keys and decoded values where possible.
    """

    decoded: dict[str, Any] = {}
    for key, value in raw_items.items():
        decoded_key = decode_redis_value(key)
        if not isinstance(decoded_key, str):
            decoded_key = str(decoded_key)
        decoded[decoded_key] = decode_redis_value(value)
    return decoded


def coerce_float(
    value: Any,
    *,
    allow_none: bool = True,
    null_sentinels: Iterable[str] = ("", "None", "null"),
    finite_only: bool = False,
) -> float | None:
    """Convert a Redis field to ``float`` with shared null handling.

    Delegates to canonical implementation in common.utils.numeric with additional
    handling for null sentinels and finite-only requirements.

    Many Redis hashes store numeric values as strings. This helper centralises
    the "treat empty/None as missing" convention and lets callers decide if a
    missing value should propagate as ``None`` or raise ``ValueError``.

    Args:
        value: Raw value from Redis.
        allow_none: When ``True`` (default) treat nulls as ``None``; otherwise
            raise ``ValueError``.
        null_sentinels: Iterable of string values that should be treated as
            nulls/empties.
        finite_only: When ``True``, reject NaN and infinity values.

    Returns:
        Parsed float or ``None`` when allowed.

    Raises:
        ValueError: If the value cannot be coerced and ``allow_none`` is ``False``.
    """
    from common.utils.numeric import coerce_float_optional

    # Early return for None
    if value is None:
        return _handle_none_value(allow_none)

    # Handle string null sentinels
    if isinstance(value, str):
        stripped = value.strip()
        if _is_null_sentinel(stripped, null_sentinels):
            return _handle_none_value(allow_none)

    # Delegate to canonical implementation
    result = coerce_float_optional(value)

    # Handle conversion failure
    if result is None:
        if allow_none:
            return None
        raise FloatCoercionError(f"Cannot coerce value to float: {value!r}")

    # Apply finite-only constraint
    if finite_only:
        import math

        if not math.isfinite(result):
            return _handle_none_value(allow_none)

    return result


def _handle_none_value(allow_none: bool) -> float | None:
    """Handle None value based on allow_none flag."""
    if allow_none:
        return None
    raise ValueError("Cannot coerce None to float")


def _is_null_sentinel(value: str, null_sentinels: Iterable[str]) -> bool:
    """Check if value matches any null sentinel."""
    value_lower = value.lower()
    return value_lower in {sentinel.lower() for sentinel in null_sentinels}
