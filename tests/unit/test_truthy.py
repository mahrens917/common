from __future__ import annotations

from common.truthy import pick_if, pick_truthy


def test_pick_truthy_returns_value_when_truthy():
    assert pick_truthy("x", "y") == "x"


def test_pick_truthy_returns_alternate_when_falsey():
    assert pick_truthy("", "y") == "y"


def test_pick_if_picks_true_branch():
    assert pick_if(True, lambda: "x", lambda: "y") == "x"


def test_pick_if_picks_false_branch():
    assert pick_if(False, lambda: "x", lambda: "y") == "y"
