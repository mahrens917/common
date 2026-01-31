"""Parse Claude JSON responses into MarketExtraction objects."""

from __future__ import annotations

import json
import logging

from ._response_parser_helpers import (
    build_dedup_mapping,
    build_id_correction_lookup,
    extract_kalshi_underlyings,
    parse_strike_value,
    process_poly_batch_items,
    validate_poly_extraction,
)
from .models import MarketExtraction

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
        Extracted underlying string (uppercased), or None if not found.

    Raises:
        json.JSONDecodeError: If response is not valid JSON.
    """
    text = strip_markdown_json(response_text)
    data = _parse_json_with_recovery(text, allow_extra_data=True)
    underlying = data.get("underlying")
    if underlying and isinstance(underlying, str):
        return underlying.upper()
    logger.debug("Missing or invalid underlying in response: %s", data)
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
    id_correction = build_id_correction_lookup(markets_data, original_ids)
    results, processed_ids = extract_kalshi_underlyings(markets_data, id_correction)
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
        groups = data["groups"]
        original_upper: set[str] | None = None
        if original_underlyings:
            original_upper = {u.upper() for u in original_underlyings}
        return build_dedup_mapping(groups, original_upper)


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
    data = _parse_json_with_recovery(text, allow_extra_data=True)

    is_valid, error = validate_poly_extraction(data, valid_categories, valid_underlyings)
    if not is_valid:
        return None, error

    floor_strike = parse_strike_value(data.get("floor_strike"))
    cap_strike = parse_strike_value(data.get("cap_strike"))

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
) -> tuple[dict[str, MarketExtraction], list[str], list[str]]:
    """Parse batch Poly extraction response with validation.

    Args:
        response_text: Raw JSON response from Claude.
        valid_categories: Set of valid categories.
        valid_underlyings: Set of valid underlyings.
        original_ids: Original market IDs for ID correction.

    Returns:
        Tuple of (valid extractions dict, failed market IDs to retry, no-match IDs to skip).
    """
    if original_ids is None:
        original_ids = []
    text = strip_markdown_json(response_text)
    data = _parse_json_with_recovery(text)

    if "markets" not in data:
        logger.warning("Missing 'markets' key in batch response")
        return {}, original_ids, []

    markets_data = data["markets"]
    id_correction = build_id_correction_lookup(markets_data, original_ids)

    return process_poly_batch_items(markets_data, id_correction, valid_categories, valid_underlyings)


def parse_expiry_alignment_response(response_text: str) -> str | None:
    """Parse expiry alignment response.

    Args:
        response_text: Raw JSON response from Claude.

    Returns:
        Aligned event_date ISO string if same event, None otherwise.

    Raises:
        json.JSONDecodeError: If response is not valid JSON.
    """
    text = strip_markdown_json(response_text)
    data = _parse_json_with_recovery(text, allow_extra_data=True)

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
