"""Strike type specific enrichers."""

from typing import Any, Dict, Optional


def enrich_greater_strike(enriched: Dict[str, Any], floor_strike: Optional[float]) -> None:
    """Enrich metadata for 'greater' strike type."""
    if floor_strike is None:
        return

    if not enriched.get("floor_strike"):
        enriched["floor_strike"] = str(floor_strike)

    cap_value = enriched.get("cap_strike")
    if not cap_value:
        enriched["cap_strike"] = "inf"


def enrich_less_strike(enriched: Dict[str, Any], cap_strike: Optional[float]) -> None:
    """Enrich metadata for 'less' strike type."""
    if cap_strike is None:
        return

    if not enriched.get("cap_strike"):
        enriched["cap_strike"] = str(cap_strike)

    floor_value = enriched.get("floor_strike")
    if not floor_value:
        enriched["floor_strike"] = "0"


def enrich_between_strike(enriched: Dict[str, Any]) -> None:
    """Enrich metadata for 'between' strike type."""
    if "floor_strike" not in enriched:
        enriched["floor_strike"] = ""
    if "cap_strike" not in enriched:
        enriched["cap_strike"] = ""


def enrich_strike_type_field(enriched: Dict[str, Any], strike_type: str) -> None:
    """Set strike_type field if not already present."""
    if not enriched.get("strike_type"):
        enriched["strike_type"] = strike_type


def enrich_strike_value_field(enriched: Dict[str, Any], strike_value: Optional[float]) -> None:
    """Set strike field if not already present."""
    if strike_value is not None and not enriched.get("strike"):
        enriched["strike"] = str(strike_value)
