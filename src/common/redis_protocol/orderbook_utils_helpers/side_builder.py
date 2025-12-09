# ruff: noqa: PLR2004, PLR0913, PLR0911, PLR0912, PLR0915, C901
"""Build orderbook sides from message data."""

from typing import Any, Dict, List

# Constants extracted for ruff PLR2004 compliance
ISINSTANCE_PRICE_LEVEL_2 = 2


def process_yes_levels(levels: List[Any]) -> Dict[str, float]:
    """
    Process yes side price levels.

    Args:
        levels: List of [price, size] tuples

    Returns:
        Dict mapping price strings to sizes
    """
    result: Dict[str, float] = {}
    for price_level in levels:
        if not (isinstance(price_level, (list, tuple)) and len(price_level) == 2):
            continue
        price, size = price_level
        if isinstance(size, (int, float)) and size > 0:
            result[str(price)] = size
    return result


def process_no_levels(levels: List[Any]) -> Dict[str, float]:
    """
    Process no side price levels (converts to yes_asks).

    Args:
        levels: List of [price, size] tuples

    Returns:
        Dict mapping converted price strings to sizes
    """
    result: Dict[str, float] = {}
    for price_level in levels:
        if not (isinstance(price_level, (list, tuple)) and len(price_level) == 2):
            continue
        price, size = price_level
        if isinstance(size, (int, float)) and size > 0:
            converted_price = 100 - float(price)
            result[str(converted_price)] = size
    return result
