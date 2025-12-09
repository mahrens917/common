"""Shared helpers for price history recording/retrieval."""

from src.common.exceptions import ValidationError


def validate_currency(currency: str) -> None:
    """Validate supported currency symbols."""
    if currency not in ("BTC", "ETH"):
        raise ValidationError(f"Invalid currency: {currency}. Must be 'BTC' or 'ETH'.")


def generate_redis_key(currency: str) -> str:
    """Generate the canonical Redis key for a currency price history."""
    return f"history:{currency.lower()}"
