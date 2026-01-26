"""Parse Claude JSON responses into MarketExtraction objects."""

from __future__ import annotations

import json
import logging

from .models import KALSHI_CATEGORIES, MarketExtraction

logger = logging.getLogger(__name__)


def strip_markdown_json(text: str) -> str:
    """Remove markdown code block wrapping from JSON text."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        return "\n".join(lines[1:-1])
    return stripped


def parse_strike_value(value: object) -> float | None:
    """Parse a strike value to float, handling strings and nulls."""
    if value is None:
        return None
    if not isinstance(value, (int, float, str)):
        raise TypeError(f"Strike value must be int, float, or str, got {type(value).__name__}")
    return float(value)


def _validate_category(category: object) -> str:
    """Validate category is a valid string from KALSHI_CATEGORIES."""
    if not isinstance(category, str):
        raise TypeError(f"category must be str, got {type(category).__name__}")
    if category not in KALSHI_CATEGORIES:
        raise ValueError(f"Invalid category: {category}")
    return category


def _parse_string_field(item: dict, field_name: str) -> str:
    """Extract and validate a required string field."""
    value = item.get(field_name)
    if not value or not isinstance(value, str):
        raise ValueError(f"Missing or invalid {field_name}: {value}")
    return value.upper() if field_name in ("underlying", "subject") else value


def _parse_scopes(item: dict, field_name: str) -> tuple[str, ...]:
    """Parse a scopes array field into a tuple of strings."""
    raw = item.get(field_name)
    if not raw or not isinstance(raw, list):
        return ()
    return tuple(str(s) for s in raw if s)


def parse_single_item(item: dict, market_id: str, platform: str) -> MarketExtraction:
    """Parse a single market item dict into a MarketExtraction."""
    category = _validate_category(item.get("category"))
    underlying = _parse_string_field(item, "underlying")
    subject = _parse_string_field(item, "subject")
    entity = _parse_string_field(item, "entity")
    scope = _parse_string_field(item, "scope")
    floor_strike = parse_strike_value(item.get("floor_strike"))
    cap_strike = parse_strike_value(item.get("cap_strike"))

    parent_entity = item.get("parent_entity")
    if parent_entity and not isinstance(parent_entity, str):
        parent_entity = str(parent_entity)
    parent_scope = item.get("parent_scope")
    if parent_scope and not isinstance(parent_scope, str):
        parent_scope = str(parent_scope)

    is_conjunction = bool(item.get("is_conjunction"))
    conjunction_scopes = _parse_scopes(item, "conjunction_scopes")
    is_union = bool(item.get("is_union"))
    union_scopes = _parse_scopes(item, "union_scopes")

    return MarketExtraction(
        market_id=market_id,
        platform=platform,
        category=category,
        underlying=underlying,
        subject=subject,
        entity=entity,
        scope=scope,
        floor_strike=floor_strike,
        cap_strike=cap_strike,
        parent_entity=parent_entity if parent_entity else None,
        parent_scope=parent_scope if parent_scope else None,
        is_conjunction=is_conjunction,
        conjunction_scopes=conjunction_scopes,
        is_union=is_union,
        union_scopes=union_scopes,
    )


def parse_batch_response(
    response_text: str, platform: str, original_ids: list[str] | None = None
) -> dict[str, MarketExtraction]:
    """Parse a batch Claude response into a dict of market_id -> MarketExtraction.

    Args:
        response_text: Raw JSON response from Claude.
        platform: "kalshi" or "poly".
        original_ids: Original market IDs from input. If provided, used to correct
            any ID mismatches from LLM response (LLMs don't reliably echo exact strings).
    """
    text = strip_markdown_json(response_text)
    data = json.loads(text)
    if "markets" not in data:
        raise KeyError("'markets' field is required in batch response")
    markets_data = data["markets"]

    # Build case-insensitive lookup from LLM ID -> original ID
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
    for item in markets_data:
        extraction = _safe_parse_item(item, platform, id_correction)
        if extraction is not None:
            results[extraction.market_id] = extraction

    return results


def _safe_parse_item(
    item: dict, platform: str, id_correction: dict[str, str] | None = None
) -> MarketExtraction | None:
    """Parse a single item, returning None if invalid or unparsable."""
    item_id = item.get("id")
    if not item_id:
        logger.warning("Skipping market with missing id in batch response")
        return None

    # Use corrected ID if available (fixes LLM not echoing exact IDs)
    market_id = str(item_id)
    if id_correction and market_id in id_correction:
        market_id = id_correction[market_id]

    # Pre-validate required fields to avoid exceptions
    validation_error = _validate_item_fields(item, market_id)
    if validation_error:
        logger.warning("Failed to parse market %s: %s", market_id, validation_error)
        return None

    return parse_single_item(item, market_id, platform)


def _validate_string_field(item: dict, field: str) -> str | None:
    """Validate a single string field. Returns error message or None."""
    value = item.get(field)
    if not value or not isinstance(value, str):
        return f"missing or invalid {field}: {value}"
    return None


def _validate_item_fields(item: dict, item_id: str) -> str | None:
    """Validate required fields exist and have correct types. Returns error message or None."""
    category = item.get("category")
    if not category or not isinstance(category, str):
        return f"missing or invalid category: {category}"
    if category not in KALSHI_CATEGORIES:
        return f"invalid category: {category}"

    for field in ("underlying", "subject", "entity", "scope"):
        error = _validate_string_field(item, field)
        if error:
            return error

    return None


__all__ = ["parse_batch_response", "parse_single_item", "parse_strike_value", "strip_markdown_json"]
