"""Strike key parsing helpers."""

from .exceptions import ProbabilityStoreError


def parse_numeric_strike(strike_key: str) -> float:
    """Parse plain numeric strike."""
    try:
        return float(strike_key)
    except ValueError as exc:  # policy_guard: allow-silent-handler
        raise ProbabilityStoreError(f"Invalid numeric strike '{strike_key}'") from exc


def parse_greater_than_strike(strike_key: str) -> float:
    """Parse >VALUE strike format."""
    try:
        return float(strike_key[1:])
    except ValueError as exc:  # policy_guard: allow-silent-handler
        raise ProbabilityStoreError(f"Invalid strike key '{strike_key}'") from exc


def parse_less_than_strike(strike_key: str) -> float:
    """Parse <VALUE strike format."""
    try:
        return float(strike_key[1:])
    except ValueError as exc:  # policy_guard: allow-silent-handler
        raise ProbabilityStoreError(f"Invalid strike key '{strike_key}'") from exc


def parse_range_strike(strike_key: str) -> float:
    """Parse range strike (START-END format)."""
    start, _, _ = strike_key.partition("-")
    try:
        return float(start)
    except ValueError as exc:  # policy_guard: allow-silent-handler
        raise ProbabilityStoreError(f"Invalid strike range '{strike_key}'") from exc
