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
    underlyings_json = json.dumps(sorted(existing_underlyings))

    return f"""You are a market data analyst. Extract the underlying asset code from a Kalshi prediction market.

EXISTING UNDERLYINGS (use one of these if it matches, only create new if none fit):
{underlyings_json}

Extract the underlying - a short uppercase code for the SPECIFIC asset/entity being measured:
  - Crypto: "BTC", "ETH", "SOL", "DOGE", "SHIB", "XRP"
  - Forex: "USDJPY", "EURUSD", "GBPUSD"
  - Weather: "NYC_KNYC", "CHI_KMDW", "DEN_KDEN", "LAX_KLAX", "MIA_KMIA", "AUS_KAUS"
  - Sports teams/leagues: "NFL", "NBA", "MLB", "UCL"
  - Esports teams: "FAZE", "G2", "SENTINELS", "FNATIC"
  - Economics: "FED", "CPI", "GDP"
  - Entertainment: "SPOTIFY_USA", "BILLBOARD_HOT100"

WEATHER STATION RULE: Weather underlyings MUST use the format CITY_STATION where STATION is the ICAO code the market resolves at.
Common mappings: New York=KNYC (Central Park), Chicago=KMDW (Midway), Denver=KDEN, Los Angeles=KLAX, Miami=KMIA, Austin=KAUS, Seattle=KSEA.
If the market rules name a specific station, use that station. If no station is stated, use the most common station for that city.

CRITICAL: Underlyings must identify SPECIFIC entities, not broad categories.
  - WRONG: "ENTERTAINMENT", "CRYPTO", "SPORTS", "WEATHER", "ESPORTS"
  - RIGHT: "SPOTIFY_USA", "BTC", "NFL", "CHI_KMDW", "FAZE"

If an existing underlying matches, use it exactly. Only create a new code if none fit.

Output ONLY valid JSON. Do NOT add any text, explanations, or reasoning.
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


def build_kalshi_underlying_batch_prompt(existing_underlyings: list[str]) -> str:
    """Build prompt for batch extracting underlyings from Kalshi markets.

    Args:
        existing_underlyings: List of already-extracted underlyings to prefer.

    Returns:
        System prompt string.
    """
    underlyings_json = json.dumps(sorted(existing_underlyings))

    return f"""You are a market data analyst. Extract the underlying asset code from multiple Kalshi prediction markets.

EXISTING UNDERLYINGS (use one of these if it matches, only create new if none fit):
{underlyings_json}

Extract the underlying - a short uppercase code for the SPECIFIC asset/entity being measured:
  - Crypto: "BTC", "ETH", "SOL", "DOGE", "SHIB", "XRP"
  - Forex: "USDJPY", "EURUSD", "GBPUSD"
  - Weather: "NYC_KNYC", "CHI_KMDW", "DEN_KDEN", "LAX_KLAX", "MIA_KMIA", "AUS_KAUS"
  - Sports teams/leagues: "NFL", "NBA", "MLB", "UCL"
  - Esports teams: "FAZE", "G2", "SENTINELS", "FNATIC"
  - Economics: "FED", "CPI", "GDP"
  - Entertainment: "SPOTIFY_USA", "BILLBOARD_HOT100"

WEATHER STATION RULE: Weather underlyings MUST use the format CITY_STATION where STATION is the ICAO code the market resolves at.
Common mappings: New York=KNYC (Central Park), Chicago=KMDW (Midway), Denver=KDEN, Los Angeles=KLAX, Miami=KMIA, Austin=KAUS, Seattle=KSEA.
If the market rules name a specific station, use that station. If no station is stated, use the most common station for that city.

CRITICAL: Underlyings must identify SPECIFIC entities, not broad categories.
  - WRONG: "ENTERTAINMENT", "CRYPTO", "SPORTS", "WEATHER", "ESPORTS"
  - RIGHT: "SPOTIFY_USA", "BTC", "NFL", "CHI_KMDW", "FAZE"

If an existing underlying matches, use it exactly. Only create a new code if none fit.

Output ONLY valid JSON. Do NOT add any text, explanations, or reasoning after the JSON.
Return a single JSON object with a "markets" array containing one object per market:
{{"markets": [{{"id": "market_id_1", "underlying": "CODE1"}}, {{"id": "market_id_2", "underlying": "CODE2"}}]}}"""


def build_kalshi_underlying_batch_user_content(markets: list[dict]) -> str:
    """Build user message for batch Kalshi underlying extraction.

    Args:
        markets: List of market dicts with 'id', 'title', 'rules_primary', 'category'.

    Returns:
        User message string with all markets.
    """
    parts: list[str] = []
    for market in markets:
        market_id = market["id"]
        title = market["title"]
        category = market["category"]
        lines = [f"[ID: {market_id}]", f"Title: {title}", f"Category: {category}"]
        rules = market.get("rules_primary")
        if rules:
            lines.append(f"Rules: {rules[:300]}")
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


def build_kalshi_dedup_prompt(category: str, underlyings: list[str]) -> str:
    """Build prompt for deduplicating underlyings within a category.

    Args:
        category: The category these underlyings belong to.
        underlyings: List of underlyings to check for duplicates.

    Returns:
        System prompt string.
    """
    underlyings_json = json.dumps(sorted(underlyings))

    return f"""You are a market data analyst. Review these underlyings from {category} markets and identify ONLY those that refer to the EXACT SAME asset.

Underlyings: {underlyings_json}

CRITICAL: Only group codes that are TRULY IDENTICAL assets with different names/tickers.

CORRECT groupings (same asset, different names):
- BTC, BITCOIN, XBT -> all refer to Bitcoin
- ETH, ETHEREUM -> both refer to Ethereum
- NDX, NASDAQ100 -> both refer to NASDAQ-100 index

INCORRECT groupings (different assets, do NOT group):
- SPX and NDX -> S&P 500 vs NASDAQ-100 are DIFFERENT indices
- BTC and ETH -> different cryptocurrencies
- NYC_KNYC and CHI_KMDW -> different cities
- NYC_KNYC and NYC_KLGA -> different weather stations in the same city, do NOT group

CORRECT weather groupings (same city AND same station):
- NYC_KNYC, NEWYORK_KNYC -> same city and station

Pick the canonical name (prefer standard ticker codes like "BTC" over "BITCOIN").

Output ONLY valid JSON. Do NOT add any text or explanations.
{{"groups": [{{"canonical": "BTC", "aliases": ["BITCOIN", "XBT"]}}]}}

If no duplicates found: {{"groups": []}}"""


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

VALID UNDERLYINGS (use one, or null if the market does not match any):
{underlyings_json}

VALID STRIKE TYPES (must use exactly one):
["greater", "less", "between"]

Extract:

1. category: Must be from the valid categories list.

2. underlying: From the valid underlyings list, or null if the market does not match any.

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

For SINGLE market, output:
{{"category": "...", "underlying": "...", "strike_type": "...", "floor_strike": <number|null>, "cap_strike": <number|null>}}

For MULTIPLE markets, output a "markets" array:
{{"markets": [{{"id": "...", "category": "...", "underlying": "...", "strike_type": "...", "floor_strike": <number|null>, "cap_strike": <number|null>}}, ...]}}

CRITICAL RULES:
- Output ONLY valid JSON. Do NOT add any text, explanations, or reasoning.
- Do NOT write "Wait, I need to reconsider" or any other commentary.
- floor_strike and cap_strike must be numbers or null, never strings.
- category and strike_type MUST be from the provided lists.
- underlying MUST be from the provided list OR null if the market measures something different from all listed underlyings.
- Do NOT force-match an underlying just because it seems related. The market must measure the SAME specific thing (e.g., box office revenue vs streaming views are DIFFERENT underlyings)."""


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


def build_expiry_alignment_prompt() -> str:
    """Build prompt for aligning Poly expiry with Kalshi expiry.

    Used in phase 2 to determine if near-miss pairs are the same event.

    Returns:
        System prompt string.
    """
    return """You are a market data analyst. Determine if two prediction markets are for the SAME EVENT.

You will be given:
- Kalshi market title and expiry time
- Poly market title and API expiry time

Rules:
1. PERIOD EVENTS (daily high, monthly max, weekly close): If both markets are betting on the same period outcome, they are the same event. Use the Kalshi expiry as the canonical time.

2. When one market says "in [period]" and the other says "on [last day of period]", they are typically the same period event — the date is the resolution date, not a point-in-time.

3. POINT-IN-TIME EVENTS (specific price at a specific moment): Only match if the times are actually the same.

4. If one market specifies "at [specific time]" (e.g., "at 5pm EST"), the event is point-in-time regardless of how the other market phrases it. The other market's different API expiry means a different settlement time — output null.

5. DIFFERENT EVENTS: If they are clearly different events (different days, different periods), output null.

Examples of SAME EVENT:
- Kalshi: "Highest temperature in Miami on Jan 28" (expiry Jan 28 23:59 ET)
- Poly: "highest temperature in Miami between 66-67°F on January 29" (expiry Jan 29 07:00 ET)
- These are the SAME daily high event. Output Kalshi's expiry.

- Kalshi: "How high will XRP get in January?" (expiry Feb 1 00:00 ET)
- Poly: "Will XRP reach $2.30 in January?" (expiry Feb 1 12:00 ET)
- These are the SAME monthly max event. Output Kalshi's expiry.

- Kalshi: "How high will XRP get in January?" (expiry Jan 31 23:59 ET)
- Poly: "Will the price of XRP be above $2.30 on January 31?" (expiry Jan 31 12:00 ET)
- "on January 31" refers to end of January resolution, same monthly event. Output Kalshi's expiry.

Examples of DIFFERENT EVENTS:
- Kalshi: "BTC price at 4pm ET on Jan 28"
- Poly: "BTC price at 5pm ET on Jan 28"
- Different times for point-in-time event. Output null.

- Kalshi: "Ethereum price on Feb 6, 2026 at 5pm EST?" (expiry 2026-02-06 22:00 UTC)
- Poly: "Will the price of Ethereum be above $2,300 on February 6?" (expiry 2026-02-06 17:00 UTC)
- Kalshi says "at 5pm EST" = point-in-time. Different settlement times. Output null.

Output ONLY valid JSON:
{"same_event": true, "event_date": "<ISO8601>"} or {"same_event": false, "event_date": null}"""


def build_expiry_alignment_user_content(
    kalshi_title: str,
    kalshi_expiry: str,
    poly_title: str,
    poly_expiry: str,
    underlying: str | None = None,
    strike_info: str | None = None,
) -> str:
    """Build user message for expiry alignment.

    Args:
        kalshi_title: Kalshi market title.
        kalshi_expiry: Kalshi expiry in ISO format.
        poly_title: Poly market title.
        poly_expiry: Poly API expiry in ISO format.
        underlying: Shared underlying asset code.
        strike_info: Strike match description.

    Returns:
        User message string.
    """
    content = f"""KALSHI:
Title: {kalshi_title}
Expiry: {kalshi_expiry}

POLY:
Title: {poly_title}
Expiry: {poly_expiry}"""

    if underlying or strike_info:
        context_parts: list[str] = []
        if underlying:
            context_parts.append(f"Underlying: {underlying}")
        if strike_info:
            context_parts.append(f"Strikes: {strike_info}")
        content += "\n\nCONTEXT:\n" + "\n".join(context_parts)

    return content


__all__ = [
    "build_kalshi_underlying_prompt",
    "build_kalshi_underlying_user_content",
    "build_kalshi_underlying_batch_prompt",
    "build_kalshi_underlying_batch_user_content",
    "build_kalshi_dedup_prompt",
    "build_poly_prompt",
    "build_poly_user_content",
    "build_expiry_alignment_prompt",
    "build_expiry_alignment_user_content",
    "build_poly_batch_user_content",
]
