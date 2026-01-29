"""Parse Claude JSON responses into MarketExtraction objects."""

from __future__ import annotations

import json
import logging
from typing import Any

from .models import VALID_POLY_STRIKE_TYPES, MarketExtraction

logger = logging.getLogger(__name__)


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
                    extra[:200] if len(extra) > 200 else extra,
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
        logger.debug("Missing or invalid underlying in response: %s", data)
        return None
    except json.JSONDecodeError as e:
        logger.debug("Failed to parse Kalshi underlying response: %s", e)
        return None


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

    # Build ID correction lookup (case-insensitive matching)
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

    # Find IDs that weren't in the response
    failed_ids = [oid for oid in original_ids if oid not in processed_ids]

    return results, failed_ids


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
        groups = data.get("groups", [])
        mapping: dict[str, str] = {}

        # Build uppercase lookup for validation
        original_upper: set[str] | None = None
        if original_underlyings:
            original_upper = {u.upper() for u in original_underlyings}

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
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Failed to parse Kalshi dedup response: %s", e)
        raise


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
        if not isinstance(floor_strike, (int, float)):
            try:
                float(floor_strike)
            except (ValueError, TypeError) as e:
                raise ValueError(f"floor_strike not numeric: {floor_strike}") from e
        floor_strike = float(floor_strike)

    if cap_strike is not None:
        if not isinstance(cap_strike, (int, float)):
            try:
                float(cap_strike)
            except (ValueError, TypeError) as e:
                raise ValueError(f"cap_strike not numeric: {cap_strike}") from e
        cap_strike = float(cap_strike)

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

    # Build ID correction lookup
    id_correction: dict[str, str] = {}
    if original_ids:
        original_lookup = {oid.upper(): oid for oid in original_ids}
        for item in markets_data:
            if item is None:
                continue
            llm_id = item.get("id")
            if llm_id:
                llm_upper = str(llm_id).upper()
                if llm_upper in original_lookup:
                    id_correction[str(llm_id)] = original_lookup[llm_upper]

    results: dict[str, MarketExtraction] = {}
    failed_ids: list[str] = []

    for item in markets_data:
        if item is None:
            continue
        item_id = item.get("id")
        if not item_id:
            continue

        market_id = str(item_id)
        if id_correction and market_id in id_correction:
            market_id = id_correction[market_id]

        is_valid, error = validate_poly_extraction(item, valid_categories, valid_underlyings)
        if not is_valid:
            # Debug level since many Poly markets don't match Kalshi coverage
            logger.debug("Validation failed for %s: %s", market_id, error)
            failed_ids.append(market_id)
            continue

        floor_strike = parse_strike_value(item.get("floor_strike"))
        cap_strike = parse_strike_value(item.get("cap_strike"))
        # close_time is set from API's end_date in crossarb, not from LLM extraction

        extraction = MarketExtraction(
            market_id=market_id,
            platform="poly",
            category=item["category"],
            underlying=item["underlying"].upper(),
            strike_type=item["strike_type"],
            floor_strike=floor_strike,
            cap_strike=cap_strike,
            close_time=None,
        )
        results[market_id] = extraction

    return results, failed_ids


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

        if not data.get("same_event"):
            return None

        event_date = data.get("event_date")
        if event_date and isinstance(event_date, str):
            return event_date

        return None
    except (json.JSONDecodeError, KeyError) as e:
        logger.debug("Failed to parse expiry alignment response: %s", e)
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
