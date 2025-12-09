"""Exposure calculation helpers for limit enforcer."""

from typing import List

from ..data_models.trading import PortfolioPosition


def calculate_total_exposure(positions: List[PortfolioPosition], monitored_positions: dict) -> int:
    """Calculate total exposure across all monitored positions."""
    total = 0
    for position in positions:
        if position.ticker not in monitored_positions:
            continue
        market_value = position.market_value_cents
        if market_value is None:
            continue
        total += abs(market_value)
    return total


def should_reduce_exposure(total_exposure: int, max_exposure: int) -> bool:
    """Check if exposure reduction is needed."""
    return total_exposure > max_exposure


def get_sorted_high_risk_positions(assessments: list) -> list:
    """Get high-risk positions sorted by risk score (highest first)."""
    high_risk_positions = [a for a in assessments if a.requires_closure]
    high_risk_positions.sort(key=lambda x: x.risk_score, reverse=True)
    return high_risk_positions
