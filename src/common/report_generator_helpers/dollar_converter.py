"""
Dollar converter for cent-to-dollar conversions.

Handles conversion of monetary values from cents to dollars.
"""


class DollarConverter:
    """Converts monetary values from cents to dollars."""

    @staticmethod
    def cents_to_dollars(cents: int) -> float:
        """
        Convert cents to dollars.

        Args:
            cents: Amount in cents

        Returns:
            Amount in dollars
        """
        return cents / 100

    @staticmethod
    def calculate_total_return(cost_cents: int, pnl_cents: int) -> float:
        """
        Calculate total return in dollars.

        Args:
            cost_cents: Cost basis in cents
            pnl_cents: P&L in cents

        Returns:
            Total return (cost + P&L) in dollars
        """
        return (cost_cents + pnl_cents) / 100

    @staticmethod
    def calculate_total_contracts(trades) -> int:
        """
        Calculate total contracts from trade list.

        Args:
            trades: List of trade records

        Returns:
            Total number of contracts
        """
        if not trades:
            return 0
        return sum(t.quantity for t in trades)

    @staticmethod
    def calculate_total_cost_dollars(trades) -> float:
        """
        Calculate total cost in dollars from trade list.

        Args:
            trades: List of trade records

        Returns:
            Total cost in dollars
        """
        if not trades:
            return 0.0
        return sum(t.cost_cents for t in trades) / 100
