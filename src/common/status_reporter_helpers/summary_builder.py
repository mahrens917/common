"""Builder for opportunities summary messages."""

from typing import List

# Constants
_CONST_2 = 2


class SummaryBuilder:
    """Builds summary messages for trading opportunities and execution results."""

    @staticmethod
    def build_opportunities_summary(opportunities_found: int, trades_executed: int, markets_closed: int = 0) -> str:
        """
        Build summary message for opportunities and trades.

        Args:
            opportunities_found: Number of trading opportunities identified
            trades_executed: Number of trades successfully executed
            markets_closed: Number of markets that were closed/expired

        Returns:
            Formatted summary message
        """
        if opportunities_found == 0:
            return "📊 No trading opportunities found"

        messages = SummaryBuilder._build_message_components(opportunities_found, trades_executed, markets_closed)

        if not messages:
            status = "All systems nominal"
        elif len(messages) == 1:
            status = messages[0]
        elif len(messages) == _CONST_2:
            status = f"{messages[0]}, {messages[1]}"
        else:
            status = f"{', '.join(messages[:-1])}, and {messages[-1]}"

        return f"📊 {status}"

    @staticmethod
    def _build_message_components(opportunities_found: int, trades_executed: int, markets_closed: int) -> List[str]:
        """Build individual message components for the summary."""
        messages = []

        if opportunities_found > 0:
            opportunity_phrase = "opportunity" if opportunities_found == 1 else "opportunities"
            messages.append(f"Found {opportunities_found} {opportunity_phrase}")

        if trades_executed > 0:
            trade_phrase = "trade executed successfully" if trades_executed == 1 else "trades executed successfully"
            messages.append(f"{trades_executed} {trade_phrase}")

        untradeable = opportunities_found - trades_executed
        if untradeable > 0:
            untradeable_phrase = "opportunity could not be traded" if untradeable == 1 else "opportunities could not be traded"
            messages.append(f"{untradeable} {untradeable_phrase}")

        if markets_closed > 0:
            market_phrase = "market closed for the day" if markets_closed == 1 else "markets closed for the day"
            messages.append(f"{markets_closed} {market_phrase}")

        return messages
