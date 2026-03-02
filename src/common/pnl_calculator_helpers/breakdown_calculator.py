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
    trade_count: int
    cost: int
    pnl: int
    wins: int


class RuleData(TypedDict):
    trade_count: int
    cost: int
    pnl: int
    wins: int


class BreakdownCalculator:
    """Computes PnL breakdowns by weather station and trading rule."""

    def __init__(self):
        self.station_normalizer = StationNameNormalizer()

    async def calculate_station_breakdown(self, trades: List[TradeRecord]) -> Dict[str, PnLBreakdown]:
        """Calculate P&L breakdown by weather station using current market values."""
        raw_stations = {trade.weather_station for trade in trades if trade.weather_station}
        station_name_cache = {raw: self.station_normalizer.standardize_station_name(raw) for raw in raw_stations}

        station_data: Dict[str, StationData] = defaultdict(lambda: StationData(trade_count=0, cost=0, pnl=0, wins=0))
        for trade in trades:
            if not trade.weather_station:
                continue
            pnl = trade.calculate_current_pnl_cents()
            station = station_name_cache[trade.weather_station]
            station_data[station]["trade_count"] += 1
            station_data[station]["cost"] += trade.cost_cents
            station_data[station]["pnl"] += pnl
            if pnl > 0:
                station_data[station]["wins"] += 1

        breakdown = {}
        for station, data in station_data.items():
            trade_count = data["trade_count"]
            win_rate = data["wins"] / trade_count

            breakdown[station] = PnLBreakdown(
                trades_count=trade_count,
                cost_cents=data["cost"],
                pnl_cents=data["pnl"],
                win_rate=win_rate,
            )

        return breakdown

    async def calculate_rule_breakdown(self, trades: List[TradeRecord]) -> Dict[str, PnLBreakdown]:
        """Calculate P&L breakdown by trading rule using current market values."""
        rule_data: Dict[str, RuleData] = defaultdict(lambda: RuleData(trade_count=0, cost=0, pnl=0, wins=0))
        for trade in trades:
            pnl = trade.calculate_current_pnl_cents()
            rule = trade.trade_rule
            rule_data[rule]["trade_count"] += 1
            rule_data[rule]["cost"] += trade.cost_cents
            rule_data[rule]["pnl"] += pnl
            if pnl > 0:
                rule_data[rule]["wins"] += 1

        breakdown = {}
        for rule, data in rule_data.items():
            trade_count = data["trade_count"]
            win_rate = data["wins"] / trade_count

            breakdown[rule] = PnLBreakdown(
                trades_count=trade_count,
                cost_cents=data["cost"],
                pnl_cents=data["pnl"],
                win_rate=win_rate,
            )

        return breakdown
