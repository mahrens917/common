import json
from pathlib import Path

import pytest

from common import kalshi_fees

_TEST_COUNT_3 = 3


def _write_config(tmp_path: Path, config: dict) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "trade_analyzer_config.json"
    config_path.write_text(json.dumps(config))
    return config_path


def test_load_trade_analyzer_config_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(kalshi_fees, "PROJECT_ROOT", tmp_path)

    with pytest.raises(FileNotFoundError):
        kalshi_fees._load_trade_analyzer_config()


def test_load_trade_analyzer_config_missing_required_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = {
        "trading_fees": {
            "general_fee_coefficient": 0.07,
            "maker_fee_coefficient": 0.0175,
            "maker_fee_products": [],
        }
    }
    _write_config(tmp_path, config)
    monkeypatch.setattr(kalshi_fees, "PROJECT_ROOT", tmp_path)

    with pytest.raises(RuntimeError) as err:
        kalshi_fees._load_trade_analyzer_config()

    assert "symbol_mappings" in str(err.value)


def test_load_trade_analyzer_config_missing_required_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = {
        "trading_fees": {
            "maker_fee_coefficient": 0.0175,
            "maker_fee_products": [],
        },
        "symbol_mappings": {"mappings": {}},
    }
    _write_config(tmp_path, config)
    monkeypatch.setattr(kalshi_fees, "PROJECT_ROOT", tmp_path)

    with pytest.raises(RuntimeError) as err:
        kalshi_fees._load_trade_analyzer_config()

    assert "general_fee_coefficient" in str(err.value)


def test_load_trade_analyzer_config_missing_mappings_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = {
        "trading_fees": {
            "general_fee_coefficient": 0.07,
            "maker_fee_coefficient": 0.0175,
            "maker_fee_products": [],
        },
        "symbol_mappings": {},
    }
    _write_config(tmp_path, config)
    monkeypatch.setattr(kalshi_fees, "PROJECT_ROOT", tmp_path)

    with pytest.raises(RuntimeError) as err:
        kalshi_fees._load_trade_analyzer_config()

    assert "mappings" in str(err.value)


def test_get_symbol_mappings_returns_configured_mapping() -> None:
    mappings = kalshi_fees.get_symbol_mappings()

    assert isinstance(mappings, dict)
    # Ensure at least one expected mapping is present from the shared config.
    assert mappings.get("BTC") == "general"


def test_calculate_fees_general_product_uses_general_coefficient() -> None:
    # 0.07 coefficient * 2 contracts * 0.30 dollars * (1 - 0.30) = 0.0294 -> 2.94 cents -> ceil -> 3
    fees = kalshi_fees.calculate_fees(contracts=2, price_cents=30, market_ticker="KXUNKNOWN")
    assert fees == _TEST_COUNT_3


def test_calculate_fees_maker_product_uses_maker_coefficient() -> None:
    # 0.0175 coefficient * 2 contracts * 0.40 dollars * (1 - 0.40) = 0.0084 -> 0.84 cents -> ceil -> 1
    fees = kalshi_fees.calculate_fees(contracts=2, price_cents=40, market_ticker="kxnba-series")
    assert fees == 1


def test_calculate_fees_rejects_negative_inputs() -> None:
    with pytest.raises(ValueError):
        kalshi_fees.calculate_fees(contracts=-1, price_cents=20, market_ticker="KXFOO")

    with pytest.raises(ValueError):
        kalshi_fees.calculate_fees(contracts=1, price_cents=-10, market_ticker="KXFOO")


def test_calculate_fees_returns_zero_for_zero_contracts_or_price() -> None:
    assert kalshi_fees.calculate_fees(contracts=0, price_cents=50, market_ticker="KXFOO") == 0
    assert kalshi_fees.calculate_fees(contracts=5, price_cents=0, market_ticker="KXFOO") == 0


def test_is_trade_profitable_after_fees_positive_profit() -> None:
    assert kalshi_fees.is_trade_profitable_after_fees(
        contracts=1,
        entry_price_cents=40,
        theoretical_price_cents=70,
        market_ticker="KXFOO",
    )


def test_is_trade_profitable_after_fees_non_positive_profit() -> None:
    assert not kalshi_fees.is_trade_profitable_after_fees(
        contracts=1,
        entry_price_cents=90,
        theoretical_price_cents=91,
        market_ticker="KXFOO",
    )


def test_is_trade_profitable_after_fees_rejects_negative_inputs() -> None:
    with pytest.raises(ValueError):
        kalshi_fees.is_trade_profitable_after_fees(
            contracts=1,
            entry_price_cents=-1,
            theoretical_price_cents=50,
            market_ticker="KXFOO",
        )

    with pytest.raises(ValueError):
        kalshi_fees.is_trade_profitable_after_fees(
            contracts=1,
            entry_price_cents=10,
            theoretical_price_cents=-5,
            market_ticker="KXFOO",
        )
