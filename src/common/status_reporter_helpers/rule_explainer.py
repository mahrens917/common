"""Trading rule explanation helpers."""


def explain_theoretical_yes_ask_sell(reason: str, price_cents: int) -> str:
    """Explain theoretical YES ask < market YES ask (sell profitable)."""
    theoretical_price = "0"
    if "(" in reason:
        theoretical_price = reason.split("(")[1].split(")")[0]
    return f"📋 Rule: Theoretical YES ask ({theoretical_price}¢) < " f"Market YES ask ({price_cents}¢) → SELL YES profitable"


def explain_theoretical_yes_bid_sell() -> str:
    """Explain theoretical YES bid < market YES bid (sell profitable)."""
    return "📋 Rule: Theoretical YES bid < Market YES bid → SELL YES profitable"


def explain_theoretical_yes_ask_buy() -> str:
    """Explain theoretical YES ask > market YES ask (buy profitable)."""
    return "📋 Rule: Theoretical YES ask > Market YES ask → BUY YES profitable"
