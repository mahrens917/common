"""
PnL breakdown calculation by station and rule.

Aggregates trades by weather station and trading rule, computing P&L metrics for each group.
"""

import logging
from collections import defaultdict
from typing import Dict, List, TypedDict

from ..data_models.trade_record import PnLBreakdown, TradeRecord
from .station_normalizer import StationNameNormalizer

logger = logging.getLogger(__name__)


class StationData(TypedDict):
    trades: List[TradeRecord]
    cost: int
    pnl: int
    wins: int


class RuleData(TypedDict):
    trades: List[TradeRecord]
    cost: int
    pnl: int
    wins: int


class BreakdownCalculator:
    """Computes PnL breakdowns by weather station and trading rule."""

    def __init__(self):
        self.station_normalizer = StationNameNormalizer()

    async def calculate_station_breakdown(
        self, trades: List[TradeRecord]
    ) -> Dict[str, PnLBreakdown]:
        """Calculate P&L breakdown by weather station using current market values."""
        station_data: Dict[str, StationData] = defaultdict(
            lambda: StationData(trades=[], cost=0, pnl=0, wins=0)
        )

        # Group trades by station with standardization and consolidation logic
        for trade in trades:
            if not trade.weather_station:
                continue

            station = self.station_normalizer.standardize_station_name(trade.weather_station)

            station_data[station]["trades"].append(trade)
            station_data[station]["cost"] += trade.cost_cents

            # Calculate current P&L for this trade - FAIL-FAST if no price data
            pnl = trade.calculate_current_pnl_cents()
            station_data[station]["pnl"] += pnl
            if pnl > 0:
                station_data[station]["wins"] += 1

        # Create breakdown objects
        breakdown = {}
        for station, data in station_data.items():
            if data["trades"]:
                win_rate = data["wins"] / len(data["trades"])
            else:
                win_rate = 0.0

            breakdown[station] = PnLBreakdown(
                trades_count=len(data["trades"]),
                cost_cents=data["cost"],
                pnl_cents=data["pnl"],
                win_rate=win_rate,
            )

        return breakdown

    async def calculate_rule_breakdown(self, trades: List[TradeRecord]) -> Dict[str, PnLBreakdown]:
        """Calculate P&L breakdown by trading rule using current market values."""
        rule_data: Dict[str, RuleData] = defaultdict(
            lambda: RuleData(trades=[], cost=0, pnl=0, wins=0)
        )

        # Group trades by rule
        for trade in trades:
            rule = trade.trade_rule
            rule_data[rule]["trades"].append(trade)
            rule_data[rule]["cost"] += trade.cost_cents

            # Calculate current P&L for this trade - FAIL-FAST if no price data
            pnl = trade.calculate_current_pnl_cents()
            rule_data[rule]["pnl"] += pnl
            if pnl > 0:
                rule_data[rule]["wins"] += 1

        # Create breakdown objects
        breakdown = {}
        for rule, data in rule_data.items():
            if data["trades"]:
                win_rate = data["wins"] / len(data["trades"])
            else:
                win_rate = 0.0

            breakdown[rule] = PnLBreakdown(
                trades_count=len(data["trades"]),
                cost_cents=data["cost"],
                pnl_cents=data["pnl"],
                win_rate=win_rate,
            )

        return breakdown
