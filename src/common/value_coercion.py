"""
Shared value coercion helpers re-exported for general-purpose usage.

These wrap the canonical utilities under ``common.redis_protocol.kalshi_store.utils_coercion``
so higher-level modules no longer need to access redis-specific helpers directly.
"""

from typing import Any, Dict, List, Optional

from common.redis_protocol.kalshi_store import utils_coercion

__all__ = [
    "bool_or_else",
    "coerce_mapping",
    "coerce_sequence",
    "convert_numeric_field",
    "float_or_else",
    "int_or_else",
    "string_or_else",
    "to_optional_float",
]


def bool_or_else(value: Any, otherwise: bool) -> bool:
    """Delegate boolean coercion to KalshiStore helpers."""
    return utils_coercion.bool_or_default(value, otherwise)


def coerce_mapping(candidate: Any) -> Dict[str, Any]:
    """Delegate mapping coercion to KalshiStore helpers."""
    return utils_coercion.coerce_mapping(candidate)


def coerce_sequence(candidate: Any) -> List[Any]:
    """Delegate sequence coercion to KalshiStore helpers."""
    return utils_coercion.coerce_sequence(candidate)


def convert_numeric_field(value: Any) -> Optional[float]:
    """Delegate numeric conversion helper."""
    return utils_coercion.convert_numeric_field(value)


def float_or_else(value: Any, otherwise: float = 0.0, **kwargs) -> float:
    """Delegate float coercion helper."""
    return utils_coercion.float_or_default(value, otherwise, **kwargs)


def int_or_else(value: Any, otherwise: int = 0) -> int:
    """Delegate integer coercion helper."""
    return utils_coercion.int_or_default(value, otherwise)


def string_or_else(value: Any, otherwise: str = "", *, trim: bool = False) -> str:
    """Delegate string coercion helper."""
    return utils_coercion.string_or_default(value, otherwise, trim=trim)


def to_optional_float(value: Any, *, context: str) -> Optional[float]:
    """Delegate optional float conversion with context."""
    return utils_coercion.to_optional_float(value, context=context)
