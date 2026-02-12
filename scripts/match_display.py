"""Display helpers for live_match_markets output."""

from __future__ import annotations

from common.llm_extractor import MarketExtraction


def print_field_extraction_results(fields: list[MarketExtraction]) -> None:
    """Print field extraction summary."""
    print("\n" + "=" * 80)
    print(f"EXTRACTED FIELDS FOR {len(fields)} POLY MARKETS")
    print("=" * 80)

    # Category distribution
    categories: dict[str, int] = {}
    for f in fields:
        categories[f.category] = categories.get(f.category, 0) + 1

    print("\nCategory distribution:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Underlying distribution (top 20)
    underlyings: dict[str, int] = {}
    for f in fields:
        underlyings[f.underlying] = underlyings.get(f.underlying, 0) + 1

    print("\nTop underlyings:")
    for underlying, count in sorted(underlyings.items(), key=lambda x: -x[1])[:20]:
        print(f"  {underlying}: {count}")

    # Sample extractions
    print("\nSample extractions:")
    for f in fields[:10]:
        floor_str = f"floor={f.floor_strike}" if f.floor_strike is not None else ""
        cap_str = f"cap={f.cap_strike}" if f.cap_strike is not None else ""
        strike_str = ", ".join(filter(None, [floor_str, cap_str])) if floor_str or cap_str else "no strikes"
        print(f"  [{f.category}] {f.underlying} ({strike_str})")


def print_field_match_results(
    matches: list[tuple[dict, MarketExtraction, dict]],
) -> None:
    """Print field-based match results."""
    print("\n" + "=" * 80)
    print(f"FIELD-BASED MATCHES: {len(matches)}")
    print("=" * 80)

    for i, (kalshi, fields, poly) in enumerate(matches, 1):
        kalshi_title = kalshi.get("event_title", kalshi.get("title", "N/A"))
        poly_title = poly.get("title", "N/A")

        print(f"\n--- Match {i} ---")
        print(f"Category: {fields.category} | Underlying: {fields.underlying}")
        print(f"KALSHI: {kalshi_title}")
        print(f"  Ticker: {kalshi.get('market_ticker', kalshi.get('ticker', ''))}")
        print(f"  Strike: floor={kalshi.get('floor_strike')}, cap={kalshi.get('cap_strike')}")
        print(f"  Expiry: {kalshi.get('close_time')}")
        print(f"POLY: {poly_title}")
        print(f"  Underlying: {fields.underlying}")
        print(f"  Strike: floor={fields.floor_strike}, cap={fields.cap_strike}")
        print(f"  Expiry: {poly.get('end_date')}")


def print_near_misses(near_misses: list[dict]) -> None:
    """Print near-miss diagnostics sorted by closest to matching."""
    if not near_misses:
        return

    def sort_key(nm: dict) -> float:
        expiry_score = nm["expiry_delta_min"] / 60.0
        floor_score = (nm["floor_pct"] or 0.0) * 100
        cap_score = (nm["cap_pct"] or 0.0) * 100
        return expiry_score + floor_score + cap_score

    sorted_misses = sorted(near_misses, key=sort_key)

    print("\n" + "=" * 80)
    print(f"NEAR MISSES (matched category+underlying, failed expiry/strike): {len(sorted_misses)}")
    print("=" * 80)

    for i, nm in enumerate(sorted_misses, 1):
        kalshi = nm["kalshi"]
        fields = nm["fields"]
        poly = nm["poly"]

        kalshi_title = kalshi.get("event_title", kalshi.get("title", "N/A"))

        parts = [f"expiry delta={nm['expiry_delta_min']:.1f}min"]
        if nm["floor_pct"] is not None:
            parts.append(f"floor delta={nm['floor_pct'] * 100:.2f}%")
        if nm["cap_pct"] is not None:
            parts.append(f"cap delta={nm['cap_pct'] * 100:.2f}%")

        print(f"\n--- Near Miss {i} ---")
        print(f"Category: {fields.category} | Underlying: {fields.underlying}")
        print(f"Deltas: {' | '.join(parts)}")
        print(f"KALSHI: {kalshi_title}")
        print(f"  Ticker: {kalshi.get('market_ticker', kalshi.get('ticker', ''))}")
        print(f"  Strike: floor={kalshi.get('floor_strike')}, cap={kalshi.get('cap_strike')}")
        print(f"  Expiry: {kalshi.get('close_time')}")
        print(f"POLY: {poly.get('title', 'N/A')}")
        print(f"  Underlying: {fields.underlying}")
        print(f"  Strike: floor={fields.floor_strike}, cap={fields.cap_strike}")
        print(f"  Expiry: {poly.get('end_date')}")
