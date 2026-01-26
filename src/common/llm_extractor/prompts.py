"""Unified prompt template for Claude-based market extraction."""

from __future__ import annotations

import json

from .models import KALSHI_CATEGORIES

_CATEGORIES_JSON = json.dumps(KALSHI_CATEGORIES)

EXTRACTION_PROMPT = f"""You are a market data analyst. Extract structured fields from prediction markets.

Valid categories (use EXACTLY one): {_CATEGORIES_JSON}

For EACH market, extract ALL of the following fields:

1. category: From the valid list above.
2. underlying: Short uppercase asset code matching Kalshi format. Examples:
   - Crypto: "BTC", "ETH", "SOL", "XRP", "DOGE"
   - Economics: "FED", "GDP", "CPI", "FOMC"
   - Sports: team abbreviations like "NYK", "LAL", "KC", "BUF"
   - Weather: station codes like "KORD", "KJFK"
   - Other: short descriptive code
3. subject: Short uppercase code for the specific entity within the underlying.
   - Rotten Tomatoes: movie abbreviation like "MER", "RSH"
   - Sports: player or event code like "MAHOMES", "SB"
   - Crypto: same as underlying (e.g., "BTC")
   - Economics: specific metric like "RATE", "PCE"
4. entity: The primary measurable entity (e.g., "BTC price", "Fed rate", "NYK wins").
5. scope: The condition or threshold (e.g., "above 100000", "cut 25bp", "win championship").
6. floor_strike: Lower bound number, or null. "above $3500" -> 3500. "between $3500 and $3600" -> 3500.
7. cap_strike: Upper bound number, or null. "below $3600" -> 3600. "between $3500 and $3600" -> 3600.
8. parent_entity: If this market implies a broader/easier condition, the parent entity. Otherwise null.
   - Strike implication: "BTC above 150000" implies "BTC above 100000" -> parent_entity = "BTC price", parent_scope = "above 100000"
   - Sports: "Lakers beat Celtics in Game 7" implies "Lakers win series" -> parent_entity = "LAL series", parent_scope = "win"
   - A market at a HIGHER threshold implies all LOWER threshold markets for the same underlying will also resolve Yes.
9. parent_scope: The scope of the parent (implied) market. Required if parent_entity is set.
10. is_conjunction: true if the market requires MULTIPLE conditions to ALL be true simultaneously.
    - Range markets: "between 100000 and 110000" requires BOTH above 100000 AND below 110000 -> is_conjunction = true
    - Combo markets: "BTC above 100k AND ETH above 5k" -> is_conjunction = true
11. conjunction_scopes: If is_conjunction is true, list each condition as a separate scope. Otherwise empty array.
    - Range: ["above 100000", "below 110000"]
    - Combo: ["BTC above 100000", "ETH above 5000"]
12. is_union: true if the market is satisfied by ANY ONE of multiple conditions.
    - "BTC or ETH above 100k" -> is_union = true
    - "Rain in NYC or Boston" -> is_union = true
13. union_scopes: If is_union is true, list each alternative condition. Otherwise empty array.
    - ["BTC above 100000", "ETH above 100000"]
    - ["rain NYC", "rain Boston"]

Return JSON: {{"markets": [{{"id": "...", "category": "...", "underlying": "...", "subject": "...", "entity": "...", "scope": "...", "floor_strike": number|null, "cap_strike": number|null, "parent_entity": string|null, "parent_scope": string|null, "is_conjunction": boolean, "conjunction_scopes": [...], "is_union": boolean, "union_scopes": [...]}}]}}

IMPORTANT: floor_strike and cap_strike must be numbers or null, never strings.
IMPORTANT: is_conjunction and is_union must be booleans.
IMPORTANT: conjunction_scopes and union_scopes must be arrays of strings."""


def build_user_content(markets: list[dict]) -> str:
    """Build the user message content from a list of market dicts.

    Each market dict must have 'id' and 'title'. Optional: 'description', 'tokens'.
    """
    parts: list[str] = []
    for market in markets:
        market_id = market["id"]
        title = market["title"]
        lines = [f"[ID: {market_id}]", f"Title: {title}"]
        if "description" in market:
            lines.append(f"Description: {market['description'][:500]}")
        if "tokens" in market:
            lines.append(f"Outcomes: {market['tokens']}")
        parts.append("\n".join(lines))
    return "\n\n---\n\n".join(parts)


__all__ = ["EXTRACTION_PROMPT", "build_user_content"]
