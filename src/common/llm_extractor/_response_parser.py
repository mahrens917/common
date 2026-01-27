"""Parse Claude JSON responses into MarketExtraction objects."""

from __future__ import annotations

import json
import logging
from typing import Any

from .models import VALID_POLY_STRIKE_TYPES, MarketExtraction

logger = logging.getLogger(__name__)


def strip_markdown_json(text: str) -> str:
    """Remove markdown code block wrapping from JSON text."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        return "\n".join(lines[1:-1])
    return stripped


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


def _parse_json_with_recovery(text: str) -> dict:
    """Parse JSON with recovery for common LLM response issues.

    Handles:
    - Extra data after valid JSON (LLM sometimes appends commentary)
    - Standard JSON parsing
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        if "Extra data" in str(e):
            decoder = json.JSONDecoder()
            data, _ = decoder.raw_decode(text)
            logger.warning("LLM response contained extra data after JSON, recovered successfully")
            return data
        raise


def parse_kalshi_underlying_response(response_text: str) -> str | None:
    """Parse Kalshi underlying extraction response.

    Args:
        response_text: Raw JSON response from Claude.

    Returns:
        Extracted underlying string (uppercased), or None if parsing fails.
    """
    try:
        text = strip_markdown_json(response_text)
        data = _parse_json_with_recovery(text)
        underlying = data.get("underlying")
        if underlying and isinstance(underlying, str):
            return underlying.upper()
        logger.warning("Missing or invalid underlying in response: %s", data)
        return None
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Failed to parse Kalshi underlying response: %s", e)
        return None


def parse_kalshi_dedup_response(response_text: str) -> dict[str, str]:
    """Parse Kalshi dedup response into alias -> canonical mapping.

    Args:
        response_text: Raw JSON response from Claude.

    Returns:
        Dict mapping aliases to their canonical form.
    """
    try:
        text = strip_markdown_json(response_text)
        data = _parse_json_with_recovery(text)
        groups = data.get("groups", [])
        mapping: dict[str, str] = {}
        for group in groups:
            canonical = group.get("canonical", "").upper()
            aliases = group.get("aliases", [])
            for alias in aliases:
                if isinstance(alias, str):
                    mapping[alias.upper()] = canonical
        return mapping
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Failed to parse Kalshi dedup response: %s", e)
        return {}


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

    floor_strike = extraction.get("floor_strike")
    cap_strike = extraction.get("cap_strike")

    if floor_strike is not None:
        try:
            floor_strike = float(floor_strike)
        except (ValueError, TypeError):
            return False, f"floor_strike not numeric: {floor_strike}"

    if cap_strike is not None:
        try:
            cap_strike = float(cap_strike)
        except (ValueError, TypeError):
            return False, f"cap_strike not numeric: {cap_strike}"

    if floor_strike is not None and cap_strike is not None and cap_strike <= floor_strike:
        return False, f"cap_strike ({cap_strike}) must be > floor_strike ({floor_strike})"

    return True, ""


def parse_poly_extraction_response(
    response_text: str,
    market_id: str,
    valid_categories: set[str],
    valid_underlyings: set[str],
) -> tuple[MarketExtraction | None, str]:
    """Parse single Poly extraction response with validation.

    Args:
        response_text: Raw JSON response from Claude.
        market_id: Market ID for the extraction.
        valid_categories: Set of valid categories.
        valid_underlyings: Set of valid underlyings.

    Returns:
        Tuple of (extraction or None, error_message).
    """
    try:
        text = strip_markdown_json(response_text)
        data = _parse_json_with_recovery(text)
    except (json.JSONDecodeError, KeyError) as e:
        return None, f"JSON parse error: {e}"

    is_valid, error = validate_poly_extraction(data, valid_categories, valid_underlyings)
    if not is_valid:
        return None, error

    try:
        floor_strike = parse_strike_value(data.get("floor_strike"))
        cap_strike = parse_strike_value(data.get("cap_strike"))
    except (TypeError, ValueError) as e:
        return None, f"strike parse error: {e}"

    extraction = MarketExtraction(
        market_id=market_id,
        platform="poly",
        category=data["category"],
        underlying=data["underlying"].upper(),
        strike_type=data["strike_type"],
        floor_strike=floor_strike,
        cap_strike=cap_strike,
    )
    return extraction, ""


def parse_poly_batch_response(
    response_text: str,
    valid_categories: set[str],
    valid_underlyings: set[str],
    original_ids: list[str] | None = None,
) -> tuple[dict[str, MarketExtraction], list[str]]:
    """Parse batch Poly extraction response with validation.

    Args:
        response_text: Raw JSON response from Claude.
        valid_categories: Set of valid categories.
        valid_underlyings: Set of valid underlyings.
        original_ids: Original market IDs for ID correction.

    Returns:
        Tuple of (valid extractions dict, list of failed market IDs).
    """
    try:
        text = strip_markdown_json(response_text)
        data = _parse_json_with_recovery(text)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Failed to parse batch response: %s", e)
        return {}, original_ids or []

    if "markets" not in data:
        logger.warning("Missing 'markets' key in batch response")
        return {}, original_ids or []

    markets_data = data["markets"]

    # Build ID correction lookup
    id_correction: dict[str, str] = {}
    if original_ids:
        original_lookup = {oid.upper(): oid for oid in original_ids}
        for item in markets_data:
            llm_id = item.get("id")
            if llm_id:
                llm_upper = str(llm_id).upper()
                if llm_upper in original_lookup:
                    id_correction[str(llm_id)] = original_lookup[llm_upper]

    results: dict[str, MarketExtraction] = {}
    failed_ids: list[str] = []

    for item in markets_data:
        item_id = item.get("id")
        if not item_id:
            continue

        market_id = str(item_id)
        if id_correction and market_id in id_correction:
            market_id = id_correction[market_id]

        is_valid, error = validate_poly_extraction(item, valid_categories, valid_underlyings)
        if not is_valid:
            logger.warning("Validation failed for %s: %s", market_id, error)
            failed_ids.append(market_id)
            continue

        try:
            floor_strike = parse_strike_value(item.get("floor_strike"))
            cap_strike = parse_strike_value(item.get("cap_strike"))
        except (TypeError, ValueError) as e:
            logger.warning("Strike parse failed for %s: %s", market_id, e)
            failed_ids.append(market_id)
            continue

        extraction = MarketExtraction(
            market_id=market_id,
            platform="poly",
            category=item["category"],
            underlying=item["underlying"].upper(),
            strike_type=item["strike_type"],
            floor_strike=floor_strike,
            cap_strike=cap_strike,
        )
        results[market_id] = extraction

    return results, failed_ids


__all__ = [
    "parse_kalshi_underlying_response",
    "parse_kalshi_dedup_response",
    "parse_poly_extraction_response",
    "parse_poly_batch_response",
    "parse_strike_value",
    "strip_markdown_json",
    "validate_poly_extraction",
]
