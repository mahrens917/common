from __future__ import annotations

"""Dependency factory for PnLCalculator."""


from dataclasses import dataclass

from ..redis_protocol.trade_store import TradeStore
from .close_date_operations import CloseDateOperations
from .daily_operations import DailyOperations
from .date_range_operations import DateRangeOperations
from .pnl_calculator import PnLCalculationEngine
from .report_generator import ReportGenerator
from .snapshot_manager import SnapshotManager
from .summary_calculator import SummaryCalculator
from .unified_pnl_calculator import UnifiedPnLCalculator
from .update_manager import UpdateManager


@dataclass
class PnLCalculatorDependencies:
    """Container for all PnLCalculator dependencies."""

    pnl_engine: PnLCalculationEngine
    report_generator: ReportGenerator
    snapshot_manager: SnapshotManager
    daily_ops: DailyOperations
    close_date_ops: CloseDateOperations
    date_range_ops: DateRangeOperations
    summary_calc: SummaryCalculator
    unified_calc: UnifiedPnLCalculator
    update_mgr: UpdateManager


class PnLCalculatorDependenciesFactory:
    """Factory for creating PnLCalculator dependencies."""

    @staticmethod
    def create(trade_store: TradeStore) -> PnLCalculatorDependencies:
        """Create all dependencies for PnLCalculator."""
        pnl_engine = PnLCalculationEngine()
        report_generator = ReportGenerator(trade_store)
        snapshot_manager = SnapshotManager(trade_store)

        daily_ops = DailyOperations(trade_store, pnl_engine)
        close_date_ops = CloseDateOperations(trade_store, report_generator)
        date_range_ops = DateRangeOperations(trade_store, report_generator)
        summary_calc = SummaryCalculator(trade_store, report_generator)
        unified_calc = UnifiedPnLCalculator(trade_store)
        update_mgr = UpdateManager(trade_store, pnl_engine, snapshot_manager)

        return PnLCalculatorDependencies(
            pnl_engine=pnl_engine,
            report_generator=report_generator,
            snapshot_manager=snapshot_manager,
            daily_ops=daily_ops,
            close_date_ops=close_date_ops,
            date_range_ops=date_range_ops,
            summary_calc=summary_calc,
            unified_calc=unified_calc,
            update_mgr=update_mgr,
        )
