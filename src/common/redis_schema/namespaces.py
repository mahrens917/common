from __future__ import annotations

"""Namespace utilities shared by Redis schema helpers."""


import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from common.exceptions import ValidationError

_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")


class RedisNamespace(str, Enum):
    """Top-level Redis key namespaces used across the stack."""

    MARKETS = "markets"
    REFERENCE = "reference"
    ANALYTICS = "analytics"
    WEATHER = "weather"
    TRADES = "trades"
    OPERATIONS = "ops"
    HISTORY = "history"
    TEMPORARY = "tmp"


@dataclass(frozen=True)
class KeyBuilder:
    """Simple helper to compose colon-delimited Redis keys."""

    namespace: RedisNamespace
    segments: tuple[str, ...]

    def render(self) -> str:
        parts = [self.namespace.value, *self.segments]
        return ":".join(parts)


def sanitize_segment(
    segment: str, *, case: Literal["lower", "upper", "unchanged"] = "lower"
) -> str:
    """Return a sanitized key segment, raising if it contains unsupported characters."""

    normalized = segment.strip().replace(" ", "_")
    if case == "lower":
        normalized = normalized.lower()
    elif case == "upper":
        normalized = normalized.upper()
    elif case == "unchanged":
        pass
    else:  # pragma: no cover - defensive branch
        raise ValueError(f"Unsupported case directive: {case!r}")

    if not _SEGMENT_RE.match(normalized):
        raise ValidationError(f"Invalid Redis key segment: {segment!r}")
    return normalized
