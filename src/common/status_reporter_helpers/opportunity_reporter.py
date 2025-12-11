"""Reporter for trade opportunity messages."""

from typing import Optional


class OpportunityReporter:
    """Formats and reports trade opportunity messages."""

    @staticmethod
    def format_opportunity(
        ticker: str,
        action: str,
        side: str,
        price_cents: int,
        reason: str,
        weather_context: Optional[str] = None,
    ) -> str:
        """
        Format trade opportunity message.

        Args:
            ticker: Market ticker
            action: Trade action (BUY/SELL)
            side: Trade side (YES/NO)
            price_cents: Price in cents
            reason: Trading rule reason
            weather_context: Optional weather context

        Returns:
            Multi-line formatted opportunity message
        """
        price_dollars = price_cents / 100
        lines = [f"\n💰 Opportunity: {action} {side} {ticker} @ ${price_dollars:.2f}"]

        if weather_context:
            lines.append(f"🌡️ Weather: {weather_context}")

        rule_explanation = OpportunityReporter._explain_trading_rule(reason, action, price_cents)
        lines.append(rule_explanation)

        return "\n".join(lines)

    @staticmethod
    def _explain_trading_rule(reason: str, action: str, price_cents: int) -> str:
        """
        Explain which trading rule was triggered.

        Args:
            reason: Trading rule reason string
            action: Trade action (BUY/SELL)
            price_cents: Price in cents

        Returns:
            Formatted rule explanation
        """
        action_upper = action.upper()
        if _is_sell_yes_ask_rule(reason, action_upper):
            theoretical_price = _extract_value_in_parentheses(reason)
            return f"📋 Rule: Theoretical YES ask ({theoretical_price}¢) < " f"Market YES ask ({price_cents}¢) → SELL YES profitable"

        if _is_sell_yes_bid_rule(reason, action_upper):
            return "📋 Rule: Theoretical YES bid < Market YES bid → SELL YES profitable"

        if _is_buy_yes_ask_rule(reason, action_upper):
            return "📋 Rule: Theoretical YES ask > Market YES ask → BUY YES profitable"

        return f"📋 Rule: {reason}"


def _extract_value_in_parentheses(text: str) -> str:
    """Extract the first value enclosed in parentheses, defaulting to '0'."""
    if "(" in text and ")" in text:
        return text.split("(", 1)[1].split(")", 1)[0]
    return "0"


def _is_sell_yes_ask_rule(reason: str, action_upper: str) -> bool:
    """Return True for SELL conditions comparing theoretical vs market ask."""
    return "t_yes_ask" in reason and "yes_ask" in reason and action_upper == "SELL"


def _is_sell_yes_bid_rule(reason: str, action_upper: str) -> bool:
    """Return True for SELL conditions comparing theoretical vs market bid."""
    return "t_yes_bid" in reason and "yes_bid" in reason and action_upper == "SELL"


def _is_buy_yes_ask_rule(reason: str, action_upper: str) -> bool:
    """Return True for BUY conditions comparing theoretical vs market ask."""
    return "t_yes_ask" in reason and "yes_ask" in reason and action_upper == "BUY"
