"""Data normalization utilities for MetadataStore"""

from typing import Dict


class DataNormalizer:
    """Normalizes Redis hash data for type-safe access"""

    @staticmethod
    def normalize_hash(raw: Dict) -> Dict[str, object]:
        """Ensure Redis hash payloads use string keys and decoded values."""
        normalized: Dict[str, object] = {}
        for key, value in raw.items():
            if isinstance(key, bytes):
                key_str = key.decode("utf-8", "ignore")
            else:
                key_str = str(key)

            if isinstance(value, bytes):
                normalized[key_str] = value.decode("utf-8", "ignore")
            else:
                normalized[key_str] = value
        return normalized

    @staticmethod
    def int_field(mapping: Dict[str, object], field: str, *, value_on_error: int = 0) -> int:
        """Extract integer field from mapping with type coercion"""
        value = mapping.get(field)
        if value is None:
            return value_on_error
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                return value_on_error
            return int(float(stripped))
        raise ValueError(f"Field '{field}' is not numeric: {value!r}")

    @staticmethod
    def float_field(mapping: Dict[str, object], field: str, *, value_on_error: float = 0.0) -> float:
        """Extract float field from mapping with type coercion"""
        value = mapping.get(field)
        if value is None:
            return value_on_error
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                return value_on_error
            return float(stripped)
        raise ValueError(f"Field '{field}' is not a float: {value!r}")
