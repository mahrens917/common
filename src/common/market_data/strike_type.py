"""Canonical strike type extraction from Kalshi market tickers.

This module provides the canonical implementation for extracting strike types
(greater, less, between) from Kalshi market tickers based on pattern matching.
"""

from typing import Optional

# Minimum dash count to indicate a structural 'between' pattern
_MIN_DASH_COUNT_STRUCTURAL = 2


def extract_strike_type_from_ticker(ticker: str, *, raise_on_failure: bool = True) -> Optional[str]:
    """
    Extract strike type from Kalshi ticker using business logic.

    Analyzes ticker patterns to determine if the market represents:
    - 'greater': price above a threshold (ABOVE, OVER, GREATER, >, GT)
    - 'less': price below a threshold (BELOW, UNDER, LESS, <, LT)
    - 'between': price within a range (BETWEEN, RANGE, or structural dashes)

    Args:
        ticker: Kalshi market ticker string
        raise_on_failure: If True, raise RuntimeError when type cannot be determined.
                         If False, return None instead.

    Returns:
        Strike type: 'greater', 'less', or 'between'
        Returns None if raise_on_failure=False and type cannot be determined

    Raises:
        RuntimeError: If strike type cannot be determined and raise_on_failure=True
    """
    ticker_upper = ticker.upper()

    # Check for common word patterns first
    strike_type = _check_word_patterns(ticker_upper)
    if strike_type:
        return strike_type

    # Fall back to structural patterns
    strike_type = _check_structural_patterns(ticker_upper)
    if strike_type:
        return strike_type

    if raise_on_failure:
        raise RuntimeError(f"Unable to determine strike_type from ticker: {ticker}")

    return None


def _check_word_patterns(ticker_upper: str) -> Optional[str]:
    """Check for common word patterns in ticker."""
    if "ABOVE" in ticker_upper or "OVER" in ticker_upper or "GREATER" in ticker_upper:
        return "greater"
    if "BELOW" in ticker_upper or "UNDER" in ticker_upper or "LESS" in ticker_upper:
        return "less"
    if "BETWEEN" in ticker_upper or "RANGE" in ticker_upper:
        return "between"
    return None


def _check_structural_patterns(ticker_upper: str) -> Optional[str]:
    """Check for structural patterns in ticker."""
    if "-" in ticker_upper and ticker_upper.count("-") >= _MIN_DASH_COUNT_STRUCTURAL:
        return "between"
    if ">" in ticker_upper or "GT" in ticker_upper:
        return "greater"
    if "<" in ticker_upper or "LT" in ticker_upper:
        return "less"
    return None
