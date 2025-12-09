"""Deterministic-friendly random helpers for the backoff manager."""

from __future__ import annotations

import random as _random
from typing import Final

_SECURE_RANDOM: Final = _random.SystemRandom()


def uniform(a: float, b: float) -> float:
    """Delegate to SystemRandom.uniform so callers can monkeypatch in tests."""

    return _SECURE_RANDOM.uniform(a, b)
