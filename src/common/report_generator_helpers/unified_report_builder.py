"""
Unified report builder for comprehensive multi-period reports.

Handles generation of unified PnL reports and data collection for charts.
"""

import logging
from datetime import timedelta
from typing import Any, Dict

from ..pnl_calculator import PnLCalculator
from ..time_utils import get_timezone_aware_date
from .daily_pnl_collector import DailyPnLCollector
from .time_period_formatter import TimePeriodFormatter
from .unified_pnl_formatter import UnifiedPnLFormatter

logger = logging.getLogger(__name__)


class UnifiedReportBuilder:
    def __init__(
        self,
        pnl_calculator: PnLCalculator,
        unified_formatter: UnifiedPnLFormatter,
        time_period_formatter: TimePeriodFormatter,
        daily_collector: DailyPnLCollector,
        timezone: str,
    ):
        self.pnl_calculator = pnl_calculator
        self.unified_formatter = unified_formatter
        self.time_period_formatter = time_period_formatter
        self.daily_collector = daily_collector
        self.timezone = timezone
        self.logger = logger

    async def generate_unified_pnl_report(self) -> str:
        today = get_timezone_aware_date(self.timezone)
        yesterday = today - timedelta(days=1)
        seven_days_ago = today - timedelta(days=7)
        thirty_days_ago = today - timedelta(days=30)

        today_pnl = await self.pnl_calculator.get_today_unified_pnl()
        yesterday_pnl = await self.pnl_calculator.get_yesterday_unified_pnl()
        today_trades = await self.pnl_calculator.trade_store.get_trades_by_date_range(today, today)
        yesterday_trades = await self.pnl_calculator.trade_store.get_trades_by_date_range(
            yesterday, yesterday
        )

        seven_day_trades, seven_day_report = (
            await self.pnl_calculator.get_date_range_trades_and_report(seven_days_ago, today)
        )
        thirty_day_trades, thirty_day_report = (
            await self.pnl_calculator.get_date_range_trades_and_report(thirty_days_ago, today)
        )

        lines = [
            "📊 **Trading Performance Summary**",
            "",
            self.unified_formatter.format_unified_pnl_section(
                f"Today ({today.strftime('%b %d, %Y')})",
                today_pnl,
                len(today_trades),
                today_trades,
            ),
            "",
            self.unified_formatter.format_unified_pnl_section(
                f"Yesterday ({yesterday.strftime('%b %d, %Y')})",
                yesterday_pnl,
                len(yesterday_trades),
                yesterday_trades,
            ),
            "",
            self.time_period_formatter.format_time_period_section(
                seven_day_report, "7-Day Trend", days_count=7, trades=seven_day_trades
            ),
            "",
            self.time_period_formatter.format_time_period_section(
                thirty_day_report, "30-Day Overview", days_count=30, trades=thirty_day_trades
            ),
        ]
        return "\n".join(lines)

    async def generate_unified_pnl_data(self) -> Dict[str, Any]:
        today = get_timezone_aware_date(self.timezone)
        seven_days_ago = today - timedelta(days=7)
        daily_pnl_with_unrealized = (
            await self.daily_collector.get_daily_pnl_with_unrealized_percentage(
                seven_days_ago, today
            )
        )
        _seven_day_trades, seven_day_report = (
            await self.pnl_calculator.get_date_range_trades_and_report(seven_days_ago, today)
        )

        station_breakdown = {}
        if seven_day_report.by_weather_station:
            station_breakdown = {
                station: breakdown.pnl_cents
                for station, breakdown in seven_day_report.by_weather_station.items()
            }

        rule_breakdown = {}
        if seven_day_report.by_rule:
            rule_breakdown = {
                rule: breakdown.pnl_cents for rule, breakdown in seven_day_report.by_rule.items()
            }

        daily_pnl_with_unrealized_dollars = (
            await self.daily_collector.get_daily_pnl_with_unrealized(seven_days_ago, today)
        )

        return {
            "daily_pnl": daily_pnl_with_unrealized,
            "daily_pnl_dollars": daily_pnl_with_unrealized_dollars,
            "station_breakdown": station_breakdown,
            "rule_breakdown": rule_breakdown,
        }
