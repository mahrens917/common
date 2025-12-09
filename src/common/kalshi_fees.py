from __future__ import annotations

"""Kalshi trading fee utilities shared across services."""

import json
import math
from typing import Any, Dict

from src.common.path_utils import get_project_root

PROJECT_ROOT = get_project_root(__file__, levels_up=2)


def _load_trade_analyzer_config() -> Dict[str, Any]:
    """Load fee configuration from ``config/trade_analyzer_config.json``."""

    config_path = PROJECT_ROOT / "config" / "trade_analyzer_config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    required_sections = ["trading_fees", "symbol_mappings"]
    for section in required_sections:
        if section not in config:
            raise RuntimeError(
                f"Required configuration section '{section}' not found in {config_path}"
            )

    trading_fees = config["trading_fees"]
    required_fee_fields = ["general_fee_coefficient", "maker_fee_coefficient", "maker_fee_products"]
    for field in required_fee_fields:
        if field not in trading_fees:
            raise RuntimeError(f"Required field '{field}' not found in trading_fees configuration")

    if "mappings" not in config["symbol_mappings"]:
        raise RuntimeError("Required 'mappings' section not found in symbol_mappings configuration")

    return config


def get_symbol_mappings() -> Dict[str, str]:
    """Return configured symbol-to-fee-category mappings."""

    config = _load_trade_analyzer_config()
    return config["symbol_mappings"]["mappings"]


def _is_maker_fee_product(market_ticker: str) -> bool:
    """Determine whether ``market_ticker`` qualifies for maker-fee pricing."""

    config = _load_trade_analyzer_config()
    maker_fee_products = config["trading_fees"]["maker_fee_products"]

    ticker_upper = market_ticker.upper()
    return any(
        ticker_upper.startswith(product_prefix.upper()) for product_prefix in maker_fee_products
    )


def calculate_fees(contracts: int, price_cents: int, market_ticker: str) -> int:
    """Compute Kalshi fees in cents for a proposed trade."""

    if contracts < 0:
        raise ValueError(f"Contracts cannot be negative: {contracts}")
    if price_cents < 0:
        raise ValueError(f"Price cannot be negative: {price_cents}")

    if contracts == 0 or price_cents == 0:
        return 0

    config = _load_trade_analyzer_config()
    if _is_maker_fee_product(market_ticker):
        fee_coefficient = config["trading_fees"]["maker_fee_coefficient"]
    else:
        fee_coefficient = config["trading_fees"]["general_fee_coefficient"]

    price_dollars = price_cents / 100.0
    fee_calculation_dollars = fee_coefficient * contracts * price_dollars * (1 - price_dollars)
    fee_calculation_cents = round(fee_calculation_dollars * 100, 10)
    return math.ceil(fee_calculation_cents)


def is_trade_profitable_after_fees(
    contracts: int,
    entry_price_cents: int,
    theoretical_price_cents: int,
    market_ticker: str,
) -> bool:
    """Return ``True`` if the trade clears Kalshi fees and remains profitable."""

    if entry_price_cents < 0:
        raise ValueError(f"Entry price cannot be negative: {entry_price_cents}")
    if theoretical_price_cents < 0:
        raise ValueError(f"Theoretical price cannot be negative: {theoretical_price_cents}")

    fees_cents = calculate_fees(contracts, entry_price_cents, market_ticker)
    gross_profit_cents = (theoretical_price_cents - entry_price_cents) * contracts
    net_profit_cents = gross_profit_cents - fees_cents
    return net_profit_cents > 0


__all__ = [
    "calculate_fees",
    "get_symbol_mappings",
    "is_trade_profitable_after_fees",
]
