"""Internal field parsing and validation for field extractor."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .field_extractor import ExtractedFields

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


def validate_underlying_field(data: dict, condition_id: str) -> str:
    """Validate and extract the underlying field from data."""
    if "underlying" not in data:
        logger.warning("Missing underlying for %s", condition_id)
        raise KeyError("underlying field is required")
    underlying = data["underlying"]
    if not isinstance(underlying, str) or not underlying:
        logger.warning("Invalid underlying for %s: %s", condition_id, underlying)
        raise ValueError(f"Invalid underlying: {underlying}")
    return underlying


def validate_category_field(data: dict, valid_categories: tuple[str, ...]) -> str:
    """Validate and extract category field from data."""
    if "category" not in data:
        raise KeyError("category field is required")
    if data["category"] not in valid_categories:
        raise ValueError(f"Invalid category: {data['category']}")
    return data["category"]


def extract_strike_values(data: dict) -> tuple[float | None, float | None]:
    """Extract floor and cap strike values from data."""
    floor_strike = None
    if "floor_strike" in data:
        floor_strike = parse_strike_value(data["floor_strike"])

    cap_strike = None
    if "cap_strike" in data:
        cap_strike = parse_strike_value(data["cap_strike"])

    return floor_strike, cap_strike


def parse_llm_response(response_text: str, condition_id: str, valid_categories: tuple[str, ...]) -> "ExtractedFields":
    """Parse LLM response into ExtractedFields."""
    from .field_extractor import ExtractedFields

    try:
        text = strip_markdown_json(response_text)
        data = json.loads(text)

        category = validate_category_field(data, valid_categories)
        underlying = validate_underlying_field(data, condition_id)
        floor_strike, cap_strike = extract_strike_values(data)

        return ExtractedFields(
            condition_id=condition_id,
            category=category,
            underlying=underlying.upper(),
            floor_strike=floor_strike,
            cap_strike=cap_strike,
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        logger.exception("Failed to parse LLM response for %s", condition_id)
        raise


def validate_batch_item_id(item: dict) -> str | None:
    """Validate and extract market ID from batch item."""
    if "id" not in item or not item["id"]:
        logger.warning("Skipping market with missing or empty id")
        return None
    return item["id"]


def validate_batch_item_category(item: dict, condition_id: str, valid_categories: tuple[str, ...]) -> str | None:
    """Validate and extract category from batch item."""
    if "category" not in item:
        logger.warning("Missing category for %s", condition_id)
        return None
    if item["category"] not in valid_categories:
        logger.warning("Invalid category for %s: %s", condition_id, item["category"])
        return None
    return item["category"]


def validate_batch_item_underlying(item: dict, condition_id: str) -> str | None:
    """Validate and extract underlying from batch item."""
    if "underlying" not in item or not item["underlying"]:
        logger.warning("Invalid underlying for %s", condition_id)
        return None
    underlying = item["underlying"]
    if not isinstance(underlying, str):
        logger.warning("Non-string underlying for %s: %s", condition_id, underlying)
        return None
    return underlying


def parse_batch_item(item: dict, valid_categories: tuple[str, ...]) -> "ExtractedFields | None":
    """Parse a single batch response item into ExtractedFields."""
    from .field_extractor import ExtractedFields

    condition_id = validate_batch_item_id(item)
    if not condition_id:
        return None

    category = validate_batch_item_category(item, condition_id, valid_categories)
    if not category:
        return None

    underlying = validate_batch_item_underlying(item, condition_id)
    if not underlying:
        return None

    floor_strike, cap_strike = extract_strike_values(item)

    return ExtractedFields(
        condition_id=condition_id,
        category=category,
        underlying=underlying.upper(),
        floor_strike=floor_strike,
        cap_strike=cap_strike,
    )


def parse_batch_response(response_text: str, valid_categories: tuple[str, ...]) -> dict[str, "ExtractedFields"]:
    """Parse batch LLM response into ExtractedFields dict."""
    from .field_extractor import ExtractedFields

    text = strip_markdown_json(response_text)
    data = json.loads(text)
    if "markets" not in data:
        raise KeyError("markets field is required in batch response")
    markets_data = data["markets"]

    results: dict[str, ExtractedFields] = {}
    for item in markets_data:
        fields = parse_batch_item(item, valid_categories)
        if fields:
            results[fields.condition_id] = fields

    return results


__all__ = [
    "strip_markdown_json",
    "parse_strike_value",
    "validate_underlying_field",
    "validate_category_field",
    "extract_strike_values",
    "parse_llm_response",
    "validate_batch_item_id",
    "validate_batch_item_category",
    "validate_batch_item_underlying",
    "parse_batch_item",
    "parse_batch_response",
]
