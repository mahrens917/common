"""Internal helpers for response parser batch processing."""

from __future__ import annotations

import logging
from typing import Any

from .models import VALID_POLY_STRIKE_TYPES, MarketExtraction

logger = logging.getLogger(__name__)


def parse_strike_value(value: object) -> float | None:
    """Parse a strike value to float, handling strings and nulls.

    Args:
        value: The value to parse (int, float, str, or None).

    Returns:
        Float value or None.

    Raises:
        TypeError: If value is not a valid type.
        ValueError: If string value cannot be converted to float.
    """
    if value is None:
        return None
    if not isinstance(value, (int, float, str)):
        raise TypeError(f"Strike value must be int, float, or str, got {type(value).__name__}")
    return float(value)


def validate_strike_value(value: Any, field_name: str) -> float | None:
    """Validate and convert a strike value to float.

    Args:
        value: The strike value to validate.
        field_name: Name of the field for error messages.

    Returns:
        Float value or None.

    Raises:
        ValueError: If value cannot be converted to float.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (ValueError, TypeError) as e:
        raise ValueError(f"{field_name} not numeric: {value}") from e


def validate_poly_extraction(
    extraction: dict[str, Any],
    valid_categories: set[str],
    valid_underlyings: set[str],
) -> tuple[bool, str]:
    """Validate Poly extraction against constraints.

    Args:
        extraction: Parsed extraction dict from LLM.
        valid_categories: Set of valid category strings.
        valid_underlyings: Set of valid underlying strings.

    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.
    """
    category = extraction.get("category")
    if category not in valid_categories:
        return False, f"invalid category: {category}"

    underlying = extraction.get("underlying")
    if underlying not in valid_underlyings:
        return False, f"invalid underlying: {underlying}"

    strike_type = extraction.get("strike_type")
    if strike_type not in VALID_POLY_STRIKE_TYPES:
        return False, f"invalid strike_type: {strike_type}"

    floor_strike = validate_strike_value(extraction.get("floor_strike"), "floor_strike")
    cap_strike = validate_strike_value(extraction.get("cap_strike"), "cap_strike")

    if floor_strike is not None and cap_strike is not None and cap_strike <= floor_strike:
        return False, f"cap_strike ({cap_strike}) must be > floor_strike ({floor_strike})"

    return True, ""


def build_id_correction_lookup(
    markets_data: list[dict[str, Any] | None],
    original_ids: list[str],
) -> dict[str, str]:
    """Build case-insensitive ID correction mapping."""
    original_lookup = {oid.upper(): oid for oid in original_ids}
    id_correction: dict[str, str] = {}
    for item in markets_data:
        if item is None:
            continue
        llm_id = item.get("id")
        if llm_id:
            llm_upper = str(llm_id).upper()
            if llm_upper in original_lookup:
                id_correction[str(llm_id)] = original_lookup[llm_upper]
    return id_correction


def extract_kalshi_underlyings(
    markets_data: list[dict[str, Any] | None],
    id_correction: dict[str, str],
) -> tuple[dict[str, str], set[str]]:
    """Extract underlying values from Kalshi batch response items."""
    results: dict[str, str] = {}
    processed_ids: set[str] = set()
    for item in markets_data:
        if item is None:
            continue
        item_id = item.get("id")
        if not item_id:
            continue
        market_id = str(item_id)
        if market_id in id_correction:
            market_id = id_correction[market_id]
        underlying = item.get("underlying")
        if underlying and isinstance(underlying, str):
            results[market_id] = underlying.upper()
            processed_ids.add(market_id)
    return results, processed_ids


def build_dedup_mapping(
    groups: list[dict[str, Any]],
    original_upper: set[str] | None,
) -> dict[str, str]:
    """Build alias->canonical mapping from dedup groups."""
    mapping: dict[str, str] = {}
    for group in groups:
        canonical = group["canonical"].upper()
        aliases = group["aliases"]
        if original_upper and canonical not in original_upper:
            logger.warning("Dedup canonical '%s' not in original underlyings, skipping group", canonical)
            continue
        for alias in aliases:
            if isinstance(alias, str):
                alias_upper = alias.upper()
                if original_upper and alias_upper not in original_upper:
                    logger.warning("Dedup alias '%s' not in original underlyings, skipping", alias_upper)
                    continue
                mapping[alias_upper] = canonical
    return mapping


def build_market_extraction(item: dict[str, Any], market_id: str) -> MarketExtraction:
    """Build a MarketExtraction from a validated item."""
    return MarketExtraction(
        market_id=market_id,
        platform="poly",
        category=item["category"],
        underlying=item["underlying"].upper(),
        strike_type=item["strike_type"],
        floor_strike=parse_strike_value(item.get("floor_strike")),
        cap_strike=parse_strike_value(item.get("cap_strike")),
        close_time=None,
    )


def process_poly_batch_items(
    markets_data: list[dict[str, Any] | None],
    id_correction: dict[str, str],
    valid_categories: set[str],
    valid_underlyings: set[str],
) -> tuple[dict[str, MarketExtraction], list[str]]:
    """Process market items from Poly batch response."""
    results: dict[str, MarketExtraction] = {}
    failed_ids: list[str] = []
    for item in markets_data:
        if item is None or not item.get("id"):
            continue
        market_id = str(item["id"])
        if id_correction and market_id in id_correction:
            market_id = id_correction[market_id]
        is_valid, error = validate_poly_extraction(item, valid_categories, valid_underlyings)
        if not is_valid:
            logger.debug("Validation failed for %s: %s", market_id, error)
            failed_ids.append(market_id)
            continue
        results[market_id] = build_market_extraction(item, market_id)
    return results, failed_ids


__all__ = [
    "build_dedup_mapping",
    "build_id_correction_lookup",
    "build_market_extraction",
    "extract_kalshi_underlyings",
    "parse_strike_value",
    "process_poly_batch_items",
    "validate_poly_extraction",
    "validate_strike_value",
]
