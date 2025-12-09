"""Strike field enrichment logic."""

from typing import Any, Dict, Optional


class StrikeEnricher:
    """Handles enrichment of strike-related metadata fields."""

    @staticmethod
    def enrich_greater_type(enriched: Dict[str, Any], floor_strike: Optional[float]) -> None:
        """Enrich fields for 'greater' strike type."""
        if floor_strike is None:
            return

        if not enriched.get("floor_strike"):
            enriched["floor_strike"] = str(floor_strike)

        cap_value = enriched.get("cap_strike")
        if not cap_value:
            enriched["cap_strike"] = "inf"

    @staticmethod
    def enrich_less_type(enriched: Dict[str, Any], cap_strike: Optional[float]) -> None:
        """Enrich fields for 'less' strike type."""
        if cap_strike is None:
            return

        if not enriched.get("cap_strike"):
            enriched["cap_strike"] = str(cap_strike)

        floor_value = enriched.get("floor_strike")
        if not floor_value:
            enriched["floor_strike"] = "0"

    @staticmethod
    def enrich_between_type(enriched: Dict[str, Any]) -> None:
        """Enrich fields for 'between' strike type."""
        if "floor_strike" not in enriched:
            enriched["floor_strike"] = ""
        if "cap_strike" not in enriched:
            enriched["cap_strike"] = ""
