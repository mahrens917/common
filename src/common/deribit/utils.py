from __future__ import annotations

"""Shared Deribit helpers."""


def is_supported_ticker(ticker: str) -> bool:
    """Return True for tickers supported by the Deribit integration."""
    normalized = ticker.strip().upper()
    if not normalized:
        return False

    # Spot tickers look like BTC_USDC and should be kept.
    if "_" in normalized and "-" not in normalized:
        base, quote = normalized.split("_", 1)
        return base in {"BTC", "ETH"} and bool(quote)

    # Reject complex instruments (e.g. spreads) that embed underscores alongside hyphens.
    if "_" in normalized and "-" in normalized:
        return False

    return normalized.startswith("BTC-") or normalized.startswith("ETH-")


__all__ = ["is_supported_ticker"]
