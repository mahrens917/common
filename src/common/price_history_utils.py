"""Shared helpers for price history recording/retrieval and sorted set member format."""

from common.exceptions import ValidationError


def validate_currency(currency: str) -> None:
    """Validate supported currency symbols."""
    if currency not in ("BTC", "ETH"):
        raise ValidationError(f"Invalid currency: {currency}. Must be 'BTC' or 'ETH'.")


def generate_redis_key(currency: str) -> str:
    """Generate the canonical Redis key for a currency price history."""
    return f"history:{currency.lower()}"


def build_history_member(int_ts: int, value: float) -> str:
    """Build a sorted set member for history keys: 'timestamp|value' format."""
    return f"{int_ts}|{value}"


def parse_history_member_value(member: str | bytes) -> float:
    """Extract the numeric value from a history sorted set member."""
    decoded = member.decode() if isinstance(member, bytes) else member
    _, value_str = decoded.split("|", 1)
    return float(value_str)
