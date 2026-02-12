import json
from pathlib import Path

import pytest

from common import kalshi_fees


def _write_config(tmp_path: Path, config: dict) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "trade_analyzer_config.json"
    config_path.write_text(json.dumps(config))
    return config_path


# ── Config loading validation ─────────────────────────────────────────


class TestLoadTradeAnalyzerConfig:

    def test_missing_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(kalshi_fees, "PROJECT_ROOT", tmp_path)
        with pytest.raises(FileNotFoundError):
            kalshi_fees._load_trade_analyzer_config()

    def test_missing_trading_fees_section(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config = {"symbol_mappings": {"mappings": {}}}
        _write_config(tmp_path, config)
        monkeypatch.setattr(kalshi_fees, "PROJECT_ROOT", tmp_path)
        with pytest.raises(RuntimeError, match="trading_fees"):
            kalshi_fees._load_trade_analyzer_config()

    def test_missing_symbol_mappings_section(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config = {
            "trading_fees": {
                "categories": {"standard": {"taker_fee_coefficient": 0.07, "maker_fee_coefficient": 0.0175}},
                "index_ticker_prefixes": [],
            },
        }
        _write_config(tmp_path, config)
        monkeypatch.setattr(kalshi_fees, "PROJECT_ROOT", tmp_path)
        with pytest.raises(RuntimeError, match="symbol_mappings"):
            kalshi_fees._load_trade_analyzer_config()

    def test_missing_categories_field(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config = {
            "trading_fees": {"index_ticker_prefixes": []},
            "symbol_mappings": {"mappings": {}},
        }
        _write_config(tmp_path, config)
        monkeypatch.setattr(kalshi_fees, "PROJECT_ROOT", tmp_path)
        with pytest.raises(RuntimeError, match="categories"):
            kalshi_fees._load_trade_analyzer_config()

    def test_missing_index_ticker_prefixes_field(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config = {
            "trading_fees": {
                "categories": {"standard": {"taker_fee_coefficient": 0.07, "maker_fee_coefficient": 0.0175}},
            },
            "symbol_mappings": {"mappings": {}},
        }
        _write_config(tmp_path, config)
        monkeypatch.setattr(kalshi_fees, "PROJECT_ROOT", tmp_path)
        with pytest.raises(RuntimeError, match="index_ticker_prefixes"):
            kalshi_fees._load_trade_analyzer_config()

    def test_missing_standard_category(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config = {
            "trading_fees": {
                "categories": {"index": {"taker_fee_coefficient": 0.035, "maker_fee_coefficient": 0.00875}},
                "index_ticker_prefixes": [],
            },
            "symbol_mappings": {"mappings": {}},
        }
        _write_config(tmp_path, config)
        monkeypatch.setattr(kalshi_fees, "PROJECT_ROOT", tmp_path)
        with pytest.raises(RuntimeError, match="standard"):
            kalshi_fees._load_trade_analyzer_config()

    def test_missing_coefficient_in_category(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config = {
            "trading_fees": {
                "categories": {"standard": {"taker_fee_coefficient": 0.07}},
                "index_ticker_prefixes": [],
            },
            "symbol_mappings": {"mappings": {}},
        }
        _write_config(tmp_path, config)
        monkeypatch.setattr(kalshi_fees, "PROJECT_ROOT", tmp_path)
        with pytest.raises(RuntimeError, match="maker_fee_coefficient"):
            kalshi_fees._load_trade_analyzer_config()

    def test_missing_mappings_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config = {
            "trading_fees": {
                "categories": {"standard": {"taker_fee_coefficient": 0.07, "maker_fee_coefficient": 0.0175}},
                "index_ticker_prefixes": [],
            },
            "symbol_mappings": {},
        }
        _write_config(tmp_path, config)
        monkeypatch.setattr(kalshi_fees, "PROJECT_ROOT", tmp_path)
        with pytest.raises(RuntimeError, match="mappings"):
            kalshi_fees._load_trade_analyzer_config()


# ── Symbol mappings ───────────────────────────────────────────────────


def test_get_symbol_mappings_returns_configured_mapping() -> None:
    mappings = kalshi_fees.get_symbol_mappings()
    assert isinstance(mappings, dict)
    assert mappings.get("BTC") == "general"


# ── Standard taker fees (coefficient 0.07) ────────────────────────────


class TestStandardTakerFees:

    def test_standard_taker_basic(self) -> None:
        # 0.07 * 2 * 0.30 * 0.70 = 0.0294 -> 2.94c -> ceil -> 3
        assert kalshi_fees.calculate_fees(2, 30, "KXUNKNOWN") == 3

    def test_standard_taker_at_midpoint(self) -> None:
        # 0.07 * 1 * 0.50 * 0.50 = 0.0175 -> 1.75c -> ceil -> 2
        assert kalshi_fees.calculate_fees(1, 50, "KXFOO") == 2

    def test_standard_taker_near_extremes(self) -> None:
        # 0.07 * 1 * 0.05 * 0.95 = 0.003325 -> 0.3325c -> ceil -> 1
        assert kalshi_fees.calculate_fees(1, 5, "KXFOO") == 1
        # 0.07 * 1 * 0.95 * 0.05 = 0.003325 -> 0.3325c -> ceil -> 1
        assert kalshi_fees.calculate_fees(1, 95, "KXFOO") == 1

    def test_standard_taker_many_contracts(self) -> None:
        # 0.07 * 100 * 0.50 * 0.50 = 1.75 -> 175c -> ceil -> 175
        assert kalshi_fees.calculate_fees(100, 50, "KXFOO") == 175

    def test_standard_taker_price_99(self) -> None:
        # 0.07 * 1 * 0.99 * 0.01 = 0.000693 -> 0.0693c -> ceil -> 1
        assert kalshi_fees.calculate_fees(1, 99, "KXFOO") == 1

    def test_standard_taker_price_1(self) -> None:
        # 0.07 * 1 * 0.01 * 0.99 = 0.000693 -> 0.0693c -> ceil -> 1
        assert kalshi_fees.calculate_fees(1, 1, "KXFOO") == 1


# ── Standard maker fees (coefficient 0.0175) ─────────────────────────


class TestStandardMakerFees:

    def test_standard_maker_basic(self) -> None:
        # 0.0175 * 2 * 0.40 * 0.60 = 0.0084 -> 0.84c -> ceil -> 1
        assert kalshi_fees.calculate_fees(2, 40, "KXFOO", is_maker=True) == 1

    def test_standard_maker_at_midpoint(self) -> None:
        # 0.0175 * 1 * 0.50 * 0.50 = 0.004375 -> 0.4375c -> ceil -> 1
        assert kalshi_fees.calculate_fees(1, 50, "KXFOO", is_maker=True) == 1

    def test_standard_maker_many_contracts(self) -> None:
        # 0.0175 * 100 * 0.50 * 0.50 = 0.4375 -> 43.75c -> ceil -> 44
        assert kalshi_fees.calculate_fees(100, 50, "KXFOO", is_maker=True) == 44

    def test_standard_maker_near_extremes(self) -> None:
        # 0.0175 * 1 * 0.05 * 0.95 = 0.00083125 -> 0.083125c -> ceil -> 1
        assert kalshi_fees.calculate_fees(1, 5, "KXFOO", is_maker=True) == 1

    def test_standard_maker_many_contracts_at_30(self) -> None:
        # 0.0175 * 10 * 0.30 * 0.70 = 0.03675 -> 3.675c -> ceil -> 4
        assert kalshi_fees.calculate_fees(10, 30, "KXFOO", is_maker=True) == 4


# ── Index taker fees (coefficient 0.035) ──────────────────────────────


class TestIndexTakerFees:

    def test_inx_taker(self) -> None:
        # 0.035 * 1 * 0.50 * 0.50 = 0.00875 -> 0.875c -> ceil -> 1
        assert kalshi_fees.calculate_fees(1, 50, "INXD-25FEB10-T5950") == 1

    def test_inx_taker_many_contracts(self) -> None:
        # 0.035 * 100 * 0.50 * 0.50 = 0.875 -> 87.5c -> ceil -> 88
        assert kalshi_fees.calculate_fees(100, 50, "INXD-25FEB10-T5950") == 88

    def test_nasdaq100_taker(self) -> None:
        # 0.035 * 2 * 0.30 * 0.70 = 0.0147 -> 1.47c -> ceil -> 2
        assert kalshi_fees.calculate_fees(2, 30, "NASDAQ100D-25FEB10-T20000") == 2

    def test_inxw_taker(self) -> None:
        # 0.035 * 10 * 0.40 * 0.60 = 0.084 -> 8.4c -> ceil -> 9
        assert kalshi_fees.calculate_fees(10, 40, "INXW-25FEB14-T5900") == 9

    def test_nasdaq100m_taker(self) -> None:
        # 0.035 * 5 * 0.60 * 0.40 = 0.042 -> 4.2c -> ceil -> 5
        assert kalshi_fees.calculate_fees(5, 60, "NASDAQ100M-25FEB") == 5

    def test_inx_taker_is_half_of_standard(self) -> None:
        standard_fee = kalshi_fees.calculate_fees(100, 50, "KXFOO")
        index_fee = kalshi_fees.calculate_fees(100, 50, "INXD-25FEB10")
        # Standard: 175, Index: 88 (175/2 = 87.5, but ceil is per-calc)
        assert index_fee < standard_fee


# ── Index maker fees (coefficient 0.00875) ────────────────────────────


class TestIndexMakerFees:

    def test_inx_maker(self) -> None:
        # 0.00875 * 1 * 0.50 * 0.50 = 0.0021875 -> 0.21875c -> ceil -> 1
        assert kalshi_fees.calculate_fees(1, 50, "INXD-25FEB10", is_maker=True) == 1

    def test_inx_maker_many_contracts(self) -> None:
        # 0.00875 * 100 * 0.50 * 0.50 = 0.21875 -> 21.875c -> ceil -> 22
        assert kalshi_fees.calculate_fees(100, 50, "INXD-25FEB10", is_maker=True) == 22

    def test_nasdaq100_maker(self) -> None:
        # 0.00875 * 10 * 0.40 * 0.60 = 0.021 -> 2.1c -> ceil -> 3
        assert kalshi_fees.calculate_fees(10, 40, "NASDAQ100D-25FEB10", is_maker=True) == 3

    def test_inx_maker_is_half_of_standard_maker(self) -> None:
        standard_maker = kalshi_fees.calculate_fees(100, 50, "KXFOO", is_maker=True)
        index_maker = kalshi_fees.calculate_fees(100, 50, "INXD-25FEB10", is_maker=True)
        # Standard maker: 44, Index maker: 22 (44/2 = 22)
        assert index_maker == 22
        assert standard_maker == 44


# ── Edge cases ────────────────────────────────────────────────────────


class TestEdgeCases:

    def test_rejects_negative_contracts(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            kalshi_fees.calculate_fees(-1, 20, "KXFOO")

    def test_rejects_negative_price(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            kalshi_fees.calculate_fees(1, -10, "KXFOO")

    def test_zero_contracts_returns_zero(self) -> None:
        assert kalshi_fees.calculate_fees(0, 50, "KXFOO") == 0

    def test_zero_price_returns_zero(self) -> None:
        assert kalshi_fees.calculate_fees(5, 0, "KXFOO") == 0

    def test_zero_contracts_maker_returns_zero(self) -> None:
        assert kalshi_fees.calculate_fees(0, 50, "KXFOO", is_maker=True) == 0

    def test_zero_price_maker_returns_zero(self) -> None:
        assert kalshi_fees.calculate_fees(5, 0, "KXFOO", is_maker=True) == 0

    def test_maker_fee_always_lte_taker_fee(self) -> None:
        for price in (10, 25, 50, 75, 90):
            taker = kalshi_fees.calculate_fees(10, price, "KXFOO")
            maker = kalshi_fees.calculate_fees(10, price, "KXFOO", is_maker=True)
            assert maker <= taker, f"Maker {maker} > taker {taker} at {price}c"

    def test_index_market_case_insensitive(self) -> None:
        upper = kalshi_fees.calculate_fees(10, 50, "INXD-25FEB10")
        lower = kalshi_fees.calculate_fees(10, 50, "inxd-25feb10")
        assert upper == lower


# ── Profitability ─────────────────────────────────────────────────────


class TestTradeProfit:

    def test_profitable_taker(self) -> None:
        assert kalshi_fees.is_trade_profitable_after_fees(
            contracts=1,
            entry_price_cents=40,
            theoretical_price_cents=70,
            market_ticker="KXFOO",
        )

    def test_not_profitable_taker(self) -> None:
        assert not kalshi_fees.is_trade_profitable_after_fees(
            contracts=1,
            entry_price_cents=90,
            theoretical_price_cents=91,
            market_ticker="KXFOO",
        )

    def test_profitable_maker(self) -> None:
        assert kalshi_fees.is_trade_profitable_after_fees(
            contracts=1,
            entry_price_cents=50,
            theoretical_price_cents=53,
            market_ticker="KXFOO",
            is_maker=True,
        )

    def test_not_profitable_maker(self) -> None:
        assert not kalshi_fees.is_trade_profitable_after_fees(
            contracts=1,
            entry_price_cents=50,
            theoretical_price_cents=51,
            market_ticker="KXFOO",
            is_maker=True,
        )

    def test_profitable_index_taker(self) -> None:
        assert kalshi_fees.is_trade_profitable_after_fees(
            contracts=1,
            entry_price_cents=50,
            theoretical_price_cents=53,
            market_ticker="INXD-25FEB10",
        )

    def test_profitable_index_maker(self) -> None:
        assert kalshi_fees.is_trade_profitable_after_fees(
            contracts=1,
            entry_price_cents=50,
            theoretical_price_cents=52,
            market_ticker="INXD-25FEB10",
            is_maker=True,
        )

    def test_rejects_negative_entry_price(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            kalshi_fees.is_trade_profitable_after_fees(
                contracts=1,
                entry_price_cents=-1,
                theoretical_price_cents=50,
                market_ticker="KXFOO",
            )

    def test_rejects_negative_theoretical_price(self) -> None:
        with pytest.raises(ValueError, match="negative"):
            kalshi_fees.is_trade_profitable_after_fees(
                contracts=1,
                entry_price_cents=10,
                theoretical_price_cents=-5,
                market_ticker="KXFOO",
            )
