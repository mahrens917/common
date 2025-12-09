"""
Report generator helpers for focused responsibilities.

This package provides specialized helpers for report generation:
- MessageFormatter: Simple message formatting
- PnLEmojiSelector: Emoji indicators for P&L values
- StatisticsCalculator: ROI, averages, and best performers
- DollarConverter: Cent-to-dollar conversions and calculations
- StationBreakdownFormatter: Weather station breakdown sections
- RuleBreakdownFormatter: Trading rule breakdown sections
- BasicPnLFormatter: Standard P&L report formatting
- CurrentDayFormatter: Current day report with unrealized P&L
- TimePeriodFormatter: Time period sections for unified reports
- UnifiedPnLFormatter: Simplified P&L sections with market values
- DailyPnLCollector: Daily P&L data collection for charts
- ReportCoordinator: Coordinates basic report generation
- SummaryReportBuilder: Builds summary stats and settlement notifications
- UnifiedReportBuilder: Builds unified multi-period reports
- CoordinatorFactory: Factory for creating coordinator instances
"""

from .basic_pnl_formatter import BasicPnLFormatter
from .coordinator_factory import CoordinatorFactory
from .current_day_formatter import CurrentDayFormatter
from .daily_pnl_collector import DailyPnLCollector
from .dollar_converter import DollarConverter
from .message_formatter import MessageFormatter
from .pnl_emoji_selector import PnLEmojiSelector
from .report_coordinator import ReportCoordinator
from .report_delegator import ReportDelegator
from .rule_breakdown_formatter import RuleBreakdownFormatter
from .station_breakdown_formatter import StationBreakdownFormatter
from .statistics_calculator import StatisticsCalculator
from .summary_report_builder import SummaryReportBuilder
from .time_period_formatter import TimePeriodFormatter
from .unified_pnl_formatter import UnifiedPnLFormatter
from .unified_report_builder import UnifiedReportBuilder

__all__ = [
    "BasicPnLFormatter",
    "CoordinatorFactory",
    "CurrentDayFormatter",
    "DailyPnLCollector",
    "DollarConverter",
    "MessageFormatter",
    "PnLEmojiSelector",
    "ReportCoordinator",
    "ReportDelegator",
    "RuleBreakdownFormatter",
    "StationBreakdownFormatter",
    "StatisticsCalculator",
    "SummaryReportBuilder",
    "TimePeriodFormatter",
    "UnifiedPnLFormatter",
    "UnifiedReportBuilder",
]
