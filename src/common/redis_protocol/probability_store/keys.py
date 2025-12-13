from __future__ import annotations

from common.truthy import pick_if

"""Key helpers for the probability store."""


from datetime import datetime
from typing import Optional, Tuple, Union

from .exceptions import ProbabilityStoreError

# Constants
_CONST_5 = 5


def strike_sort_key(strike_key: str) -> tuple[int, float]:
    """Generate a deterministic sort key for strike identifiers."""
    plain_float = _try_parse_float(strike_key)
    if plain_float is not None:
        return (0, plain_float)

    prefixed_key = _parse_prefixed_key(strike_key)
    if prefixed_key is not None:
        return prefixed_key

    range_key = _parse_range_key(strike_key)
    if range_key is not None:
        return range_key

    raise ProbabilityStoreError(f"Unsupported strike key '{strike_key}'")


def _try_parse_float(strike_key: str) -> Optional[float]:
    """Attempt to parse the strike as a plain float."""
    try:
        return float(strike_key)
    except ValueError:  # policy_guard: allow-silent-handler
        return None


def _parse_prefixed_key(strike_key: str) -> Optional[tuple[int, float]]:
    """Parse keys with > or < prefixes."""
    prefix = strike_key[:1]
    if prefix not in {">", "<"}:
        return None

    try:
        numeric_value = float(strike_key[1:])
    except ValueError as exc:  # policy_guard: allow-silent-handler
        raise ProbabilityStoreError(f"Invalid strike key '{strike_key}'") from exc

    return (pick_if(prefix == ">", lambda: 1, lambda: -1), numeric_value)


def _parse_range_key(strike_key: str) -> Optional[tuple[int, float]]:
    """Parse strike range keys (e.g., '10-20')."""
    if "-" not in strike_key:
        return None

    start, _, _ = strike_key.partition("-")
    try:
        return (0, float(start))
    except ValueError as exc:  # policy_guard: allow-silent-handler
        raise ProbabilityStoreError(f"Invalid strike range '{strike_key}'") from exc


def expiry_sort_key(expiry_key: str) -> Union[datetime, str]:
    """Normalize expiry keys for chronological sorting."""
    if "T" in expiry_key:
        return datetime.fromisoformat(expiry_key.replace("Z", "+00:00"))
    return expiry_key


def parse_probability_key(key_str: str) -> Tuple[str, str, str]:
    """Parse a probability key into expiry, strike type, and strike components."""
    parts = key_str.split(":")
    if len(parts) < _CONST_5:
        raise ProbabilityStoreError(f"Invalid probability key format: {key_str}")

    if len(parts) > _CONST_5:
        expiry = ":".join(parts[2:-2])
        strike_type = parts[-2]
        strike = parts[-1]
    else:
        expiry = parts[2]
        strike_type = parts[3]
        strike = parts[4]

    if not expiry:
        raise ProbabilityStoreError(f"Could not extract expiry from key: {key_str}")

    return expiry, strike_type, strike


__all__ = ["strike_sort_key", "expiry_sort_key", "parse_probability_key"]
