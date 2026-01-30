"""Parse Claude JSON responses into MarketExtraction objects."""

from __future__ import annotations

import json
import logging
from typing import Any

from .models import VALID_POLY_STRIKE_TYPES, MarketExtraction

logger = logging.getLogger(__name__)

# Maximum characters to show when logging truncated extra text from LLM responses
_MAX_EXTRA_TEXT_LOG_LENGTH = 200


class ExtraDataInResponse(Exception):
    """Raised when LLM response contains extra data after valid JSON."""

    def __init__(self, extra_text: str) -> None:
        self.extra_text = extra_text
        super().__init__(f"Extra data after JSON: {extra_text[:100]}")


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


def _parse_json_with_recovery(text: str, *, allow_extra_data: bool = False) -> dict:
    """Parse JSON with optional recovery for common LLM response issues.

    Args:
        text: JSON text to parse.
        allow_extra_data: If True, recover from extra data after JSON.
            If False (default), raise ExtraDataInResponse.

    Raises:
        ExtraDataInResponse: If extra data detected and allow_extra_data is False.
        json.JSONDecodeError: If JSON is malformed.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        if "Extra data" in str(e):
            decoder = json.JSONDecoder()
            data, end_idx = decoder.raw_decode(text)
            extra = text[end_idx:].strip()
            if allow_extra_data:
                logger.debug(
                    "LLM response contained extra data after JSON, recovered. Extra text: %r",
                    extra[:_MAX_EXTRA_TEXT_LOG_LENGTH] if len(extra) > _MAX_EXTRA_TEXT_LOG_LENGTH else extra,
                )
                return data
            raise ExtraDataInResponse(extra) from e
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
        # Single-market extraction is used for retries, so allow extra data recovery
        data = _parse_json_with_recovery(text, allow_extra_data=True)
        underlying = data.get("underlying")
        if underlying and isinstance(underlying, str):
            return underlying.upper()
    except json.JSONDecodeError:
        logger.debug("Failed to parse Kalshi underlying response")
        return None
    else:
        logger.debug("Missing or invalid underlying in response: %s", data)
        return None


def _build_id_correction_lookup(
    markets_data: list[dict[str, Any] | None],
    original_ids: list[str],
) -> dict[str, str]:
    """Build case-insensitive ID correction mapping.

    Args:
        markets_data: List of market items from LLM response.
        original_ids: Original market IDs for correction.

    Returns:
        Dict mapping LLM IDs to original IDs.
    """
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


def _extract_kalshi_underlyings(
    markets_data: list[dict[str, Any] | None],
    id_correction: dict[str, str],
) -> tuple[dict[str, str], set[str]]:
    """Extract underlying values from Kalshi batch response items.

    Args:
        markets_data: List of market items from LLM response.
        id_correction: ID correction mapping.

    Returns:
        Tuple of (results dict, set of processed IDs).
    """
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


def parse_kalshi_underlying_batch_response(
    response_text: str,
    original_ids: list[str],
) -> tuple[dict[str, str], list[str]]:
    """Parse batch Kalshi underlying extraction response.

    Args:
        response_text: Raw JSON response from Claude.
        original_ids: Original market IDs for ID correction.

    Returns:
        Tuple of (dict mapping market_id -> underlying, list of failed IDs).
    """
    text = strip_markdown_json(response_text)
    data = _parse_json_with_recovery(text)

    if "markets" not in data:
        logger.warning("Missing 'markets' key in Kalshi batch response")
        return {}, original_ids

    markets_data = data["markets"]
    id_correction = _build_id_correction_lookup(markets_data, original_ids)
    results, processed_ids = _extract_kalshi_underlyings(markets_data, id_correction)
    failed_ids = [oid for oid in original_ids if oid not in processed_ids]

    return results, failed_ids


def _build_dedup_mapping(
    groups: list[dict[str, Any]],
    original_upper: set[str] | None,
) -> dict[str, str]:
    """Build alias->canonical mapping from dedup groups.

    Args:
        groups: List of dedup group dicts with 'canonical' and 'aliases'.
        original_upper: Optional uppercased set of original underlyings for validation.

    Returns:
        Dict mapping aliases to their canonical form.
    """
    mapping: dict[str, str] = {}
    for group in groups:
        canonical = group.get("canonical", "").upper()
        aliases = group.get("aliases", [])

        # Validate canonical exists in original set
        if original_upper and canonical not in original_upper:
            logger.warning(
                "Dedup canonical '%s' not in original underlyings, skipping group",
                canonical,
            )
            continue

        for alias in aliases:
            if isinstance(alias, str):
                alias_upper = alias.upper()
                # Validate alias exists in original set
                if original_upper and alias_upper not in original_upper:
                    logger.warning(
                        "Dedup alias '%s' not in original underlyings, skipping",
                        alias_upper,
                    )
                    continue
                mapping[alias_upper] = canonical

    return mapping


def parse_kalshi_dedup_response(
    response_text: str,
    original_underlyings: set[str] | None = None,
) -> dict[str, str]:
    """Parse Kalshi dedup response into alias -> canonical mapping.

    Args:
        response_text: Raw JSON response from Claude.
        original_underlyings: Optional set of original underlyings for validation.
            If provided, only mappings where both canonical and alias exist
            in the original set are kept.

    Returns:
        Dict mapping aliases to their canonical form.
    """
    try:
        text = strip_markdown_json(response_text)
        data = _parse_json_with_recovery(text)
    except (json.JSONDecodeError, KeyError):
        logger.warning("Failed to parse Kalshi dedup response", exc_info=True)
        raise
    else:
        groups = data.get("groups", [])
        original_upper: set[str] | None = None
        if original_underlyings:
            original_upper = {u.upper() for u in original_underlyings}
        return _build_dedup_mapping(groups, original_upper)


def _validate_strike_value(value: Any, field_name: str) -> float | None:
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

    floor_strike = _validate_strike_value(extraction.get("floor_strike"), "floor_strike")
    cap_strike = _validate_strike_value(extraction.get("cap_strike"), "cap_strike")

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
    text = strip_markdown_json(response_text)
    # Single-market extraction is used for retries, so handle errors gracefully
    try:
        data = _parse_json_with_recovery(text, allow_extra_data=True)
    except json.JSONDecodeError as e:
        return None, f"malformed JSON: {e}"

    is_valid, error = validate_poly_extraction(data, valid_categories, valid_underlyings)
    if not is_valid:
        return None, error

    floor_strike = parse_strike_value(data.get("floor_strike"))
    cap_strike = parse_strike_value(data.get("cap_strike"))
    # close_time is set from API's end_date in crossarb, not from LLM extraction

    extraction = MarketExtraction(
        market_id=market_id,
        platform="poly",
        category=data["category"],
        underlying=data["underlying"].upper(),
        strike_type=data["strike_type"],
        floor_strike=floor_strike,
        cap_strike=cap_strike,
        close_time=None,
    )
    return extraction, ""


def _build_market_extraction(item: dict[str, Any], market_id: str) -> MarketExtraction:
    """Build a MarketExtraction from a validated item.

    Args:
        item: Validated extraction dict from LLM.
        market_id: Market ID for the extraction.

    Returns:
        MarketExtraction object.
    """
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


def _process_poly_batch_items(
    markets_data: list[dict[str, Any] | None],
    id_correction: dict[str, str],
    valid_categories: set[str],
    valid_underlyings: set[str],
) -> tuple[dict[str, MarketExtraction], list[str]]:
    """Process market items from Poly batch response.

    Args:
        markets_data: List of market items from LLM response.
        id_correction: ID correction mapping.
        valid_categories: Set of valid categories.
        valid_underlyings: Set of valid underlyings.

    Returns:
        Tuple of (valid extractions dict, list of failed market IDs).
    """
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

        results[market_id] = _build_market_extraction(item, market_id)

    return results, failed_ids


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
    text = strip_markdown_json(response_text)
    data = _parse_json_with_recovery(text)

    if "markets" not in data:
        logger.warning("Missing 'markets' key in batch response")
        return {}, original_ids or []

    markets_data = data["markets"]
    id_correction = _build_id_correction_lookup(markets_data, original_ids or [])

    return _process_poly_batch_items(markets_data, id_correction, valid_categories, valid_underlyings)


def parse_expiry_alignment_response(response_text: str) -> str | None:
    """Parse expiry alignment response.

    Args:
        response_text: Raw JSON response from Claude.

    Returns:
        Aligned event_date ISO string if same event, None otherwise.
    """
    try:
        text = strip_markdown_json(response_text)
        data = _parse_json_with_recovery(text, allow_extra_data=True)
    except (json.JSONDecodeError, KeyError):
        logger.debug("Failed to parse expiry alignment response", exc_info=True)
        return None
    else:
        if not data.get("same_event"):
            return None

        event_date = data.get("event_date")
        if event_date and isinstance(event_date, str):
            return event_date

        return None


__all__ = [
    "ExtraDataInResponse",
    "parse_kalshi_underlying_response",
    "parse_kalshi_underlying_batch_response",
    "parse_kalshi_dedup_response",
    "parse_poly_extraction_response",
    "parse_poly_batch_response",
    "parse_expiry_alignment_response",
    "parse_strike_value",
    "strip_markdown_json",
    "validate_poly_extraction",
]
