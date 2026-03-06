"""Formatting functions for status messages, trades, opportunities, and time durations."""

from __future__ import annotations

from typing import Optional

from common.truthy import pick_if

# Constants
_CONST_2 = 2
_CONST_60 = 60


# --- Basic status messages ---


def tracking_started() -> str:
    """Format tracking started message."""
    return "🔍 Tracking..."


def markets_closed() -> str:
    """Format markets closed message."""
    return "🔒 Markets closed - waiting for next check"


def markets_open() -> str:
    """Format markets open message."""
    return "✅ Markets open for trading"


def scanning_markets(market_count: int) -> str:
    """Format scanning markets message."""
    return f"🔍 Scanning {market_count} markets for opportunities..."


def initialization_complete() -> str:
    """Format initialization complete message."""
    return "🚀 Tracker initialized and ready"


def shutdown_complete() -> str:
    """Format shutdown complete message."""
    return "🛑 Tracker shutdown complete"


def checking_market_hours() -> str:
    """Format checking market hours message."""
    return "🕐 Checking market hours..."


def error_occurred(error_message: str) -> str:
    """Format error message."""
    return f"❌ Error: {error_message}"


# --- Time formatting ---


def format_wait_duration(seconds: int) -> str:
    """Format wait duration in human-readable format."""
    if seconds >= _CONST_60:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds == 0:
            if minutes == 1:
                return "1 minute"
            return f"{minutes} minutes"
        return f"{minutes}m {remaining_seconds}s"

    if seconds == 1:
        return "1 second"
    return f"{seconds} seconds"


def waiting_for_next_scan(seconds: int) -> str:
    """Format waiting for next scan message."""
    time_str = format_wait_duration(seconds)
    return f"⏳ Waiting {time_str} until next scan"


# --- Summary building ---


def build_opportunities_summary(opportunities_found: int, trades_executed: int, markets_closed: int = 0) -> str:
    """Build summary message for opportunities and trades."""
    if opportunities_found == 0:
        return "📊 No trading opportunities found"

    messages = _build_message_components(opportunities_found, trades_executed, markets_closed)

    if not messages:
        status = "All systems nominal"
    elif len(messages) == 1:
        status = messages[0]
    elif len(messages) == _CONST_2:
        status = f"{messages[0]}, {messages[1]}"
    else:
        status = f"{', '.join(messages[:-1])}, and {messages[-1]}"

    return f"📊 {status}"


def _build_message_components(opportunities_found: int, trades_executed: int, markets_closed: int) -> list[str]:
    """Build individual message components for the summary."""
    messages: list[str] = []

    if opportunities_found > 0:
        opportunity_phrase = pick_if(opportunities_found == 1, lambda: "opportunity", lambda: "opportunities")
        messages.append(f"Found {opportunities_found} {opportunity_phrase}")

    if trades_executed > 0:
        trade_phrase = pick_if(trades_executed == 1, lambda: "trade executed successfully", lambda: "trades executed successfully")
        messages.append(f"{trades_executed} {trade_phrase}")

    untradeable = opportunities_found - trades_executed
    if untradeable > 0:
        untradeable_phrase = pick_if(
            untradeable == 1, lambda: "opportunity could not be traded", lambda: "opportunities could not be traded"
        )
        messages.append(f"{untradeable} {untradeable_phrase}")

    if markets_closed > 0:
        market_phrase = pick_if(markets_closed == 1, lambda: "market closed for the day", lambda: "markets closed for the day")
        messages.append(f"{markets_closed} {market_phrase}")

    return messages


# --- Trade reporting ---


def format_trade_executed(ticker: str, action: str, side: str, price_cents: int, order_id: str) -> str:
    """Format trade execution success message."""
    price_dollars = price_cents / 100
    return f"✅ Trade executed: {action} {side} {ticker} @ " f"${price_dollars:.2f} (Order: {order_id})"


def format_trade_failed(ticker: str, reason: str) -> str:
    """Format trade failure message."""
    return f"❌ Trade failed for {ticker}: {reason}"


def format_insufficient_balance(ticker: str, required_cents: int, available_cents: int) -> str:
    """Format insufficient balance message."""
    required_dollars = required_cents / 100
    available_dollars = available_cents / 100
    return f"💸 Insufficient balance for {ticker}: " f"need ${required_dollars:.2f}, have ${available_dollars:.2f}"


def format_balance_updated(old_balance_cents: int, new_balance_cents: int) -> str:
    """Format balance update message."""
    old_dollars = old_balance_cents / 100
    new_dollars = new_balance_cents / 100
    change_dollars = (new_balance_cents - old_balance_cents) / 100

    change_sign = pick_if(change_dollars >= 0, lambda: "+", lambda: "")

    return f"💰 Balance updated: ${old_dollars:.2f} → ${new_dollars:.2f} " f"({change_sign}${change_dollars:.2f})"


# --- Opportunity reporting ---


def format_opportunity(
    ticker: str,
    action: str,
    side: str,
    price_cents: int,
    reason: str,
    weather_context: Optional[str] = None,
) -> str:
    """Format trade opportunity message."""
    price_dollars = price_cents / 100
    lines = [f"\n💰 Opportunity: {action} {side} {ticker} @ ${price_dollars:.2f}"]

    if weather_context:
        lines.append(f"🌡️ Weather: {weather_context}")

    rule_explanation = _explain_trading_rule(reason, action, price_cents)
    lines.append(rule_explanation)

    return "\n".join(lines)


def _explain_trading_rule(reason: str, action: str, price_cents: int) -> str:
    """Explain which trading rule was triggered."""
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
    """Extract the first value enclosed in parentheses."""
    if "(" in text and ")" in text:
        return text.split("(", 1)[1].split(")", 1)[0]
    return "0"


def _is_sell_yes_ask_rule(reason: str, action_upper: str) -> bool:
    """Return True for SELL conditions comparing theoretical vs market ask."""
    return "t_ask" in reason and "yes_ask" in reason and action_upper == "SELL"


def _is_sell_yes_bid_rule(reason: str, action_upper: str) -> bool:
    """Return True for SELL conditions comparing theoretical vs market bid."""
    return "t_bid" in reason and "yes_bid" in reason and action_upper == "SELL"


def _is_buy_yes_ask_rule(reason: str, action_upper: str) -> bool:
    """Return True for BUY conditions comparing theoretical vs market ask."""
    return "t_ask" in reason and "yes_ask" in reason and action_upper == "BUY"


# --- Rule explanation (alternate entry points) ---


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
