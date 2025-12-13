"""Helpers for selecting truthy values without boolean fallbacks."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")
U = TypeVar("U")


def pick_truthy(value: T, alternate: U) -> T | U:
    if value:
        return value
    return alternate


def pick_if(condition: object, if_true: Callable[[], T], if_false: Callable[[], U]) -> T | U:
    if condition:
        return if_true()
    return if_false()


__all__ = ["pick_truthy", "pick_if"]
