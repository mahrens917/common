from __future__ import annotations

"""
Property descriptor for automatic delegation to PropertyAccessor.

This allows the main class to have clean property syntax while delegating
to the helper without duplicating all property definitions.
"""

from typing import Any, Optional


class DelegatedProperty:
    """Descriptor that delegates property access to PropertyAccessor."""

    def __init__(self, name: str) -> None:
        self.name = name

    def __get__(self, obj: Any, _objtype: Optional[type] = None) -> Any:
        if obj is None:
            return self
        return getattr(obj._properties, self.name)

    def __set__(self, obj: Any, value: Any) -> None:
        setattr(obj._properties, self.name, value)
