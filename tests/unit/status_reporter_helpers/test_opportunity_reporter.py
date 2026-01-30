import pytest

from common.status_reporter_helpers.opportunity_reporter import (
    OpportunityReporter,
    _extract_value_in_parentheses,
    _is_buy_yes_ask_rule,
    _is_sell_yes_ask_rule,
    _is_sell_yes_bid_rule,
)


class TestOpportunityReporter:
    def test_format_opportunity_basic(self):
        result = OpportunityReporter.format_opportunity(
            ticker="KXBT-25JAN01",
            action="BUY",
            side="YES",
            price_cents=50,
            reason="Just a good trade",
            weather_context=None,
        )
        assert "💰 Opportunity: BUY YES KXBT-25JAN01 @ $0.50" in result
        assert "🌡️ Weather" not in result
        assert "📋 Rule: Just a good trade" in result

    def test_format_opportunity_with_weather(self):
        result = OpportunityReporter.format_opportunity(
            ticker="KXBT-25JAN01",
            action="SELL",
            side="NO",
            price_cents=150,
            reason="Another reason",
            weather_context="Sunny 25C",
        )
        assert "💰 Opportunity: SELL NO KXBT-25JAN01 @ $1.50" in result
        assert "🌡️ Weather: Sunny 25C" in result
        assert "📋 Rule: Another reason" in result

    def test_explain_trading_rule_sell_yes_ask(self):
        reason = "t_ask (40) < yes_ask (50)"
        result = OpportunityReporter._explain_trading_rule(reason, "SELL", 50)
        assert "Theoretical YES ask (40¢) < Market YES ask (50¢) → SELL YES profitable" in result

    def test_explain_trading_rule_sell_yes_bid(self):
        reason = "t_bid < yes_bid"
        result = OpportunityReporter._explain_trading_rule(reason, "SELL", 50)
        assert "Theoretical YES bid < Market YES bid → SELL YES profitable" in result

    def test_explain_trading_rule_buy_yes_ask(self):
        reason = "t_ask > yes_ask"
        result = OpportunityReporter._explain_trading_rule(reason, "BUY", 50)
        assert "Theoretical YES ask > Market YES ask → BUY YES profitable" in result

    def test_explain_trading_rule_generic(self):
        result = OpportunityReporter._explain_trading_rule("Generic reason", "BUY", 50)
        assert "📋 Rule: Generic reason" in result


class TestOpportunityReporterHelpers:
    def test_extract_value_in_parentheses(self):
        assert _extract_value_in_parentheses("Value (10)") == "10"
        assert _extract_value_in_parentheses("No value") == "0"
        assert _extract_value_in_parentheses("Empty ()") == ""

    def test_is_sell_yes_ask_rule(self):
        assert _is_sell_yes_ask_rule("t_ask < yes_ask", "SELL") is True
        assert _is_sell_yes_ask_rule("t_ask < yes_ask", "BUY") is False
        assert _is_sell_yes_ask_rule("other", "SELL") is False

    def test_is_sell_yes_bid_rule(self):
        assert _is_sell_yes_bid_rule("t_bid < yes_bid", "SELL") is True
        assert _is_sell_yes_bid_rule("t_bid < yes_bid", "BUY") is False
        assert _is_sell_yes_bid_rule("other", "SELL") is False

    def test_is_buy_yes_ask_rule(self):
        assert _is_buy_yes_ask_rule("t_ask > yes_ask", "BUY") is True
        assert _is_buy_yes_ask_rule("t_ask > yes_ask", "SELL") is False
        assert _is_buy_yes_ask_rule("other", "BUY") is False
