import pytest

from common.status_reporter_helpers.rule_explainer import (
    explain_theoretical_yes_ask_buy,
    explain_theoretical_yes_ask_sell,
    explain_theoretical_yes_bid_sell,
)


class TestRuleExplainer:
    def test_explain_theoretical_yes_ask_sell(self):
        reason = "t_yes_ask (40) < yes_ask"
        result = explain_theoretical_yes_ask_sell(reason, 50)
        assert "Theoretical YES ask (40¢) < Market YES ask (50¢) → SELL YES profitable" in result

    def test_explain_theoretical_yes_ask_sell_no_parens(self):
        reason = "t_yes_ask < yes_ask"
        result = explain_theoretical_yes_ask_sell(reason, 50)
        assert "Theoretical YES ask (0¢) < Market YES ask (50¢) → SELL YES profitable" in result

    def test_explain_theoretical_yes_bid_sell(self):
        result = explain_theoretical_yes_bid_sell()
        assert "Theoretical YES bid < Market YES bid → SELL YES profitable" in result

    def test_explain_theoretical_yes_ask_buy(self):
        result = explain_theoretical_yes_ask_buy()
        assert "Theoretical YES ask > Market YES ask → BUY YES profitable" in result
