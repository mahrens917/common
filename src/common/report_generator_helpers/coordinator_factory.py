"""
Factory for creating report coordinator instances.

Centralizes the initialization logic for all report generation coordinators.
"""

from typing import Tuple

from ..pnl_calculator import PnLCalculator
from .basic_pnl_formatter import BasicPnLFormatter
from .current_day_formatter import CurrentDayFormatter
from .daily_pnl_collector import DailyPnLCollector
from .dollar_converter import DollarConverter
from .message_formatter import MessageFormatter
from .pnl_emoji_selector import PnLEmojiSelector
from .report_coordinator import ReportCoordinator
from .rule_breakdown_formatter import RuleBreakdownFormatter
from .station_breakdown_formatter import StationBreakdownFormatter
from .statistics_calculator import StatisticsCalculator
from .summary_report_builder import SummaryReportBuilder
from .time_period_formatter import TimePeriodFormatter
from .unified_pnl_formatter import UnifiedPnLFormatter
from .unified_report_builder import UnifiedReportBuilder


class CoordinatorFactory:
    """Factory for creating report coordinators with proper dependencies."""

    @staticmethod
    def create_coordinators(
        pnl_calculator: PnLCalculator, timezone: str
    ) -> Tuple[MessageFormatter, ReportCoordinator, SummaryReportBuilder, UnifiedReportBuilder]:
        """
        Create all report coordinators with proper dependency injection.

        Args:
            pnl_calculator: P&L calculator for data generation
            timezone: Configured timezone for date calculations

        Returns:
            Tuple of (message_formatter, report_coordinator, summary_builder, unified_builder)
        """
        # Initialize base utilities
        emoji_selector = PnLEmojiSelector()
        stats_calculator = StatisticsCalculator()
        dollar_converter = DollarConverter()
        message_formatter = MessageFormatter()

        # Initialize section formatters
        station_formatter = StationBreakdownFormatter(emoji_selector)
        rule_formatter = RuleBreakdownFormatter(emoji_selector)
        basic_pnl_formatter = BasicPnLFormatter(emoji_selector, station_formatter, rule_formatter)
        current_day_formatter = CurrentDayFormatter(
            emoji_selector, station_formatter, rule_formatter
        )
        time_period_formatter = TimePeriodFormatter(emoji_selector, dollar_converter)
        unified_pnl_formatter = UnifiedPnLFormatter(
            emoji_selector, dollar_converter, stats_calculator
        )
        daily_pnl_collector = DailyPnLCollector(pnl_calculator)

        # Initialize coordinators
        report_coordinator = ReportCoordinator(
            pnl_calculator, basic_pnl_formatter, current_day_formatter, timezone
        )
        summary_builder = SummaryReportBuilder(pnl_calculator, stats_calculator, timezone)
        unified_builder = UnifiedReportBuilder(
            pnl_calculator,
            unified_pnl_formatter,
            time_period_formatter,
            daily_pnl_collector,
            timezone,
        )

        return message_formatter, report_coordinator, summary_builder, unified_builder
