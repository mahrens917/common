from __future__ import annotations

"""Lightweight registry for schema-managed Redis keys."""


from typing import Dict

_registered_prefixes: Dict[str, str] = {}


def register_namespace(prefix: str, description: str) -> None:
    """Record a managed key prefix for observability tooling."""

    if prefix in _registered_prefixes:
        if _registered_prefixes[prefix] != description:
            raise ValueError(f"Prefix {prefix!r} already registered with different description")
        return
    _registered_prefixes[prefix] = description


def validate_registered_key(key: str) -> None:
    """Ensure a key begins with a registered prefix, raising on mismatch."""

    for prefix in _registered_prefixes:
        if key.startswith(prefix):
            return
    raise ValueError(f"Key {key!r} does not match any registered Redis schema prefix")
