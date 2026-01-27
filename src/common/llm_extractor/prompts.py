"""Dynamic prompt builders for Claude-based market extraction."""

from __future__ import annotations

import json


def build_kalshi_underlying_prompt(existing_underlyings: list[str]) -> str:
    """Build prompt for extracting underlying from Kalshi markets.

    Args:
        existing_underlyings: List of already-extracted underlyings to prefer.

    Returns:
        System prompt string.
    """
    underlyings_json = json.dumps(sorted(existing_underlyings)) if existing_underlyings else "[]"

    return f"""You are a market data analyst. Extract the underlying asset code from a Kalshi prediction market.

EXISTING UNDERLYINGS (use one of these if it matches, only create new if none fit):
{underlyings_json}

Extract the underlying - a short uppercase code for the asset/entity being measured:
  - Crypto: "BTC", "ETH", "SOL", "DOGE", "SHIB"
  - Forex: "USDJPY", "EURUSD", "GBPUSD"
  - Weather: "NYC", "CHI", "SEA", "LAX", "DEN"
  - Sports: "NFL", "NBA", "MLB", "UCL"
  - Economics: "FED", "CPI", "GDP"
  - Entertainment: "SPOTIFY", "BILLBOARD"

If an existing underlying matches, use it exactly. Only create a new code if none fit.

Return JSON:
{{"underlying": "..."}}"""


def build_kalshi_underlying_user_content(title: str, rules_primary: str, category: str) -> str:
    """Build user message for Kalshi underlying extraction.

    Args:
        title: Market title.
        rules_primary: Market rules/description.
        category: Market category from Kalshi API.

    Returns:
        User message string.
    """
    lines = [f"Title: {title}", f"Category: {category}"]
    if rules_primary:
        lines.append(f"Rules: {rules_primary[:500]}")
    return "\n".join(lines)


def build_kalshi_dedup_prompt(category: str, underlyings: list[str]) -> str:
    """Build prompt for deduplicating underlyings within a category.

    Args:
        category: The category these underlyings belong to.
        underlyings: List of underlyings to check for duplicates.

    Returns:
        System prompt string.
    """
    underlyings_json = json.dumps(sorted(underlyings))

    return f"""You are a market data analyst. Review these underlyings extracted from {category} markets and identify any that refer to the same asset.

Underlyings: {underlyings_json}

Group any duplicates. Pick the best canonical name for each group (prefer shorter, standard codes like "BTC" over "BITCOIN").

Return JSON:
{{"groups": [{{"canonical": "BTC", "aliases": ["BITCOIN", "XBT"]}}, {{"canonical": "ETH", "aliases": ["ETHEREUM"]}}]}}

If no duplicates found, return: {{"groups": []}}"""


def build_poly_prompt(
    valid_categories: list[str],
    valid_underlyings: list[str],
) -> str:
    """Build prompt for extracting fields from Poly markets.

    Args:
        valid_categories: List of valid categories (from Kalshi API).
        valid_underlyings: List of valid underlyings (from Kalshi LLM extraction).

    Returns:
        System prompt string.
    """
    categories_json = json.dumps(sorted(valid_categories))
    underlyings_json = json.dumps(sorted(valid_underlyings))

    return f"""You are a market data analyst. Extract structured fields from a Polymarket prediction market.

VALID CATEGORIES (must use exactly one):
{categories_json}

VALID UNDERLYINGS (must use exactly one):
{underlyings_json}

VALID STRIKE TYPES (must use exactly one):
["greater", "less", "between"]

Extract:

1. category: Must be from the valid categories list.

2. underlying: Must be from the valid underlyings list.

3. strike_type: Must be one of: "greater", "less", "between"
   - "greater": market resolves YES if value is above threshold
   - "less": market resolves YES if value is below threshold
   - "between": market resolves YES if value is within range

4. floor_strike: Lower bound number, or null.
   - "above $3500" -> 3500
   - "between $3500 and $3600" -> 3500
   - "at least -5" -> -5
   - No threshold -> null

5. cap_strike: Upper bound number, or null.
   - "below $3600" -> 3600
   - "between $3500 and $3600" -> 3600
   - No threshold -> null

Return JSON:
{{"category": "...", "underlying": "...", "strike_type": "...", "floor_strike": <number|null>, "cap_strike": <number|null>}}

IMPORTANT: floor_strike and cap_strike must be numbers or null, never strings.
IMPORTANT: category, underlying, and strike_type MUST be from the provided lists."""


def build_poly_user_content(title: str, description: str) -> str:
    """Build user message for Poly extraction.

    Args:
        title: Market title.
        description: Market description.

    Returns:
        User message string.
    """
    lines = [f"Title: {title}"]
    if description:
        lines.append(f"Description: {description[:500]}")
    return "\n".join(lines)


def build_poly_batch_user_content(markets: list[dict]) -> str:
    """Build user message for batch Poly extraction.

    Args:
        markets: List of market dicts with 'id', 'title', and optional 'description'.

    Returns:
        User message string with all markets.
    """
    parts: list[str] = []
    for market in markets:
        market_id = market["id"]
        title = market["title"]
        lines = [f"[ID: {market_id}]", f"Title: {title}"]
        description = market.get("description")
        if description:
            lines.append(f"Description: {description[:500]}")
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


__all__ = [
    "build_kalshi_underlying_prompt",
    "build_kalshi_underlying_user_content",
    "build_kalshi_dedup_prompt",
    "build_poly_prompt",
    "build_poly_user_content",
    "build_poly_batch_user_content",
]
