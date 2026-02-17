from __future__ import annotations

"""Kalshi trading fee utilities shared across services.

Fee formula: ``ceil(coefficient * contracts * P * (1 - P))`` where *P* is the
contract price in dollars and the coefficient depends on the market category
and whether the order is maker or taker.

Categories
----------
- **standard** – most markets.  Taker 7 %, maker 1.75 %.
- **index** – S&P 500 (``INX*``) and Nasdaq-100 (``NASDAQ100*``) markets.
  Taker 3.5 %, maker 0.875 % (halved from standard).
"""

import json
import math
from typing import Any, Dict

from common.constants.trading import MAX_PRICE_CENTS
from common.path_utils import get_project_root

PROJECT_ROOT = get_project_root(__file__, levels_up=2)

_STANDARD_CATEGORY = "standard"
_MAKER_FEE_KEY = "maker_fee_coefficient"
_TAKER_FEE_KEY = "taker_fee_coefficient"


def _validate_config(config: Dict[str, Any], config_path: str) -> None:
    """Validate required sections and fields in trade analyzer config."""

    for section in ("trading_fees", "symbol_mappings"):
        if section not in config:
            raise RuntimeError(f"Required configuration section '{section}' not found in {config_path}")

    trading_fees = config["trading_fees"]
    for field in ("categories", "index_ticker_prefixes"):
        if field not in trading_fees:
            raise RuntimeError(f"Required field '{field}' not found in trading_fees configuration")

    categories = trading_fees["categories"]
    if _STANDARD_CATEGORY not in categories:
        raise RuntimeError("Required 'standard' category not found in trading_fees.categories")

    for cat_name, cat_cfg in categories.items():
        for coeff in (_TAKER_FEE_KEY, _MAKER_FEE_KEY):
            if coeff not in cat_cfg:
                raise RuntimeError(f"Required field '{coeff}' not found in category '{cat_name}'")

    if "mappings" not in config["symbol_mappings"]:
        raise RuntimeError("Required 'mappings' section not found in symbol_mappings configuration")


def _load_trade_analyzer_config() -> Dict[str, Any]:
    """Load fee configuration from ``config/trade_analyzer_config.json``."""

    config_path = PROJECT_ROOT / "config" / "trade_analyzer_config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    _validate_config(config, str(config_path))
    return config


def get_symbol_mappings() -> Dict[str, str]:
    """Return configured symbol-to-fee-category mappings."""

    config = _load_trade_analyzer_config()
    return config["symbol_mappings"]["mappings"]


def _get_market_category(market_ticker: str, config: Dict[str, Any]) -> str:
    """Return the fee category for *market_ticker* (e.g. ``'standard'`` or ``'index'``)."""

    ticker_upper = market_ticker.upper()
    index_prefixes = config["trading_fees"]["index_ticker_prefixes"]

    if any(ticker_upper.startswith(prefix.upper()) for prefix in index_prefixes):
        return "index"

    return _STANDARD_CATEGORY


def calculate_fees(
    contracts: int,
    price_cents: int,
    market_ticker: str,
    *,
    is_maker: bool = False,
) -> int:
    """Compute Kalshi fees in cents for a proposed trade.

    Parameters
    ----------
    contracts:
        Number of contracts.
    price_cents:
        Price per contract in cents (0-99).
    market_ticker:
        Ticker string used to resolve the market fee category.
    is_maker:
        ``True`` when the order rests on the book (maker); ``False`` when the
        order crosses the spread (taker).
    """

    if contracts < 0:
        raise ValueError(f"Contracts cannot be negative: {contracts}")
    if price_cents < 0:
        raise ValueError(f"Price cannot be negative: {price_cents}")
    if price_cents > MAX_PRICE_CENTS:
        raise ValueError(f"Price cannot exceed {MAX_PRICE_CENTS} cents: {price_cents}")

    if contracts == 0 or price_cents == 0:
        return 0

    config = _load_trade_analyzer_config()
    category = _get_market_category(market_ticker, config)
    fee_key = _MAKER_FEE_KEY if is_maker else _TAKER_FEE_KEY
    fee_coefficient = config["trading_fees"]["categories"][category][fee_key]

    price_dollars = price_cents / 100.0
    fee_calculation_dollars = fee_coefficient * contracts * price_dollars * (1 - price_dollars)
    fee_calculation_cents = round(fee_calculation_dollars * 100, 10)
    return math.ceil(fee_calculation_cents)


def is_trade_profitable_after_fees(
    contracts: int,
    trade_price_cents: int,
    theoretical_price_cents: int,
    market_ticker: str,
    *,
    is_maker: bool = False,
    action: str = "buy",
) -> bool:
    """Return ``True`` if the trade clears Kalshi fees and remains profitable.

    Parameters
    ----------
    trade_price_cents:
        The price of the proposed trade in cents.  For BUY this is the
        purchase price; for SELL this is the sell (exit) price.
    theoretical_price_cents:
        The fair-value reference price in cents.
    action:
        ``"buy"`` or ``"sell"``.

    For BUY:  gross = (theoretical - trade_price) * contracts.
    For SELL: gross = (trade_price - theoretical) * contracts.

    Fees are computed on *trade_price_cents* (the price of the proposed
    order).  Prior buy-side fees are sunk costs and excluded.
    """

    if trade_price_cents < 0:
        raise ValueError(f"Trade price cannot be negative: {trade_price_cents}")
    if theoretical_price_cents < 0:
        raise ValueError(f"Theoretical price cannot be negative: {theoretical_price_cents}")

    action_lower = action.lower()
    if action_lower not in ("buy", "sell"):
        raise ValueError(f"Action must be 'buy' or 'sell', got: {action!r}")

    fees_cents = calculate_fees(contracts, trade_price_cents, market_ticker, is_maker=is_maker)
    if action_lower == "buy":
        gross_profit_cents = (theoretical_price_cents - trade_price_cents) * contracts
    else:
        gross_profit_cents = (trade_price_cents - theoretical_price_cents) * contracts
    net_profit_cents = gross_profit_cents - fees_cents
    return net_profit_cents > 0


__all__ = [
    "calculate_fees",
    "get_symbol_mappings",
    "is_trade_profitable_after_fees",
]
