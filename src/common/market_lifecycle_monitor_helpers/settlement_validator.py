"""Settlement P&L validation."""

import logging
from typing import Optional, Tuple

from ..data_models.trading import PortfolioPosition
from .pnl_calculator import PnLCalculator
from .state_tracker import StateTracker

logger = logging.getLogger(__name__)


class SettlementValidator:
    """Validates settlement P&L calculations."""

    def __init__(self, state_tracker: StateTracker):
        """
        Initialize settlement validator.

        Args:
            state_tracker: State tracker with settlement cache
        """
        self.state_tracker = state_tracker
        self.pnl_calculator = PnLCalculator()

    async def validate_settlement_pnl(self, ticker: str, position_before_settlement: PortfolioPosition) -> Tuple[bool, str, Optional[int]]:
        """
        Validate P&L calculation after market settlement.

        Args:
            ticker: Settled market ticker
            position_before_settlement: Position before settlement

        Returns:
            Tuple of (is_valid, message, expected_pnl_cents)
        """
        try:
            settlement_info = self.state_tracker.settlement_cache.get(ticker)
            if not settlement_info or not settlement_info.is_settled:
                return False, "Market not settled", None

            if settlement_info.settlement_price_cents is None:
                _none_guard_value = False, "No settlement price available", None
                return _none_guard_value

            expected_pnl = self.pnl_calculator.calculate_settlement_pnl(settlement_info, position_before_settlement)

            if expected_pnl is None:
                _none_guard_value = False, "Cannot calculate P&L", None
                return _none_guard_value

            logger.info(f"[SettlementValidator] Settlement P&L for {ticker}: {expected_pnl}¢")

        except (  # policy_guard: allow-silent-handler
            AttributeError,
            ValueError,
            TypeError,
        ):
            logger.exception(f"[SettlementValidator] Error validating settlement P&L for : ")
            return False, f"P&L validation error", None
        else:
            return True, "Settlement P&L calculated", expected_pnl
