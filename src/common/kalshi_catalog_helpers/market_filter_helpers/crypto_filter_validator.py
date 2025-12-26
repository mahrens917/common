"""Crypto market filter validation."""

import re
from typing import Dict, Tuple

_CRYPTO_MONTH_PATTERN = re.compile(r"\d{2}(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\d{2}")
_CRYPTO_ASSETS: Tuple[str, ...] = ("BTC", "ETH")
_VALID_CRYPTO_STRIKE_TYPES: Tuple[str, ...] = (
    "greater",
    "less",
    "greater_or_equal",
    "less_or_equal",
    "between",
)


def validate_ticker_format(ticker: str) -> bool:
    """Validate ticker has required crypto format."""
    asset_present = bool(ticker) and any(asset in ticker for asset in _CRYPTO_ASSETS)
    if not asset_present or not _CRYPTO_MONTH_PATTERN.search(ticker):
        return False
    try:
        import importlib

        for module_path in ["src.pdf.utils.validation_helpers", "pdf.utils.validation_helpers"]:
            try:
                module = importlib.import_module(module_path)
            except (ImportError, ModuleNotFoundError, AttributeError):  # policy_guard: allow-silent-handler
                # Try alternate module path if this one is not available
                continue
            else:
                return module.ValidationHelpers.validate_ticker_format(ticker)
        else:
            return False
    except (ValueError, TypeError, AttributeError):  # Expected data validation or parsing failure  # policy_guard: allow-silent-handler
        # Validation helper rejected the ticker format
        return False


def validate_strike_type(strike_type: object) -> bool:
    """Validate strike type is valid for crypto markets."""
    return strike_type in _VALID_CRYPTO_STRIKE_TYPES


def validate_strike_values(market: Dict[str, object]) -> bool:
    """Validate strike values are properly configured."""
    cap_strike = market.get("cap_strike")
    floor_strike = market.get("floor_strike")

    if cap_strike is None and floor_strike is None:
        return False
    if cap_strike is not None and floor_strike is not None and cap_strike == floor_strike:
        return False
    return True
