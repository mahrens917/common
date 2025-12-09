"""P&L calculator for settlements."""

from typing import Optional

from ..data_models.trading import PortfolioPosition
from .state_tracker import SettlementInfo


class PnLCalculator:
    """Calculates expected P&L from settlements."""

    @staticmethod
    def calculate_settlement_pnl(
        settlement_info: SettlementInfo, position: PortfolioPosition
    ) -> Optional[int]:
        """
        Calculate expected P&L from settlement.

        Args:
            settlement_info: Settlement information
            position: Position before settlement

        Returns:
            Expected realized P&L in cents or None if cannot calculate
        """
        settlement_price = settlement_info.settlement_price_cents
        if settlement_price is None:
            return None
        side = position.side
        if side is None:
            return None
        average_price = position.average_price_cents
        position_count = position.position_count
        if position_count is None:
            return None
        if average_price is None:
            return None

        if side.value.upper() == "YES":
            settlement_value_per_contract = settlement_price
        else:
            settlement_value_per_contract = 100 - settlement_price

        total_settlement_value = settlement_value_per_contract * position_count
        cost_basis = average_price * position_count
        return total_settlement_value - cost_basis
