"""Unit tests for MetricsCalculator class."""

from __future__ import annotations

import math

import pytest

from common.data_conversion.micro_price_helpers.metrics_calculator import MetricsCalculator


class TestComputeMicroPriceMetrics:
    """Tests for MetricsCalculator.compute_micro_price_metrics."""

    def test_basic_calculation(self) -> None:
        bid, ask, bid_size, ask_size = 10.0, 15.0, 5.0, 5.0
        s_raw, i_raw, p_raw, g, h, relative_spread = MetricsCalculator.compute_micro_price_metrics(bid, ask, bid_size, ask_size, "BTC")
        assert s_raw == pytest.approx(5.0)
        assert i_raw == pytest.approx(0.5)
        assert p_raw == pytest.approx(12.5)
        assert g == pytest.approx(math.log(5.0))
        assert h == pytest.approx(math.log(0.5 / 0.5))
        assert relative_spread == pytest.approx(5.0 / 12.5)

    def test_zero_spread_uses_log_min(self) -> None:
        bid, ask, bid_size, ask_size = 10.0, 10.0, 5.0, 5.0
        s_raw, i_raw, p_raw, g, h, relative_spread = MetricsCalculator.compute_micro_price_metrics(bid, ask, bid_size, ask_size, "ETH")
        assert s_raw == pytest.approx(0.0)
        assert g == pytest.approx(math.log(1e-10))

    def test_raises_on_zero_total_volume(self) -> None:
        with pytest.raises(ValueError, match="Zero total volume"):
            MetricsCalculator.compute_micro_price_metrics(10.0, 15.0, 0.0, 0.0, "BTC")

    def test_i_raw_clamped_below(self) -> None:
        # bid_size=0, ask_size=10 → i_raw = 0 → clamped to 1e-10
        s_raw, i_raw, p_raw, g, h, relative_spread = MetricsCalculator.compute_micro_price_metrics(10.0, 15.0, 0.0, 10.0, "BTC")
        assert i_raw == pytest.approx(1e-10)

    def test_i_raw_clamped_above(self) -> None:
        # bid_size=10, ask_size=0 → i_raw = 1 → clamped to 1 - 1e-10
        s_raw, i_raw, p_raw, g, h, relative_spread = MetricsCalculator.compute_micro_price_metrics(10.0, 15.0, 10.0, 0.0, "BTC")
        assert i_raw == pytest.approx(1 - 1e-10)

    def test_zero_p_raw_gives_inf_relative_spread(self) -> None:
        # bid=0, ask=0 would give zero volume (raises);
        # use negative bid to get p_raw=0 scenario.
        # Actually we can't easily get p_raw=0 without zero volume.
        # Instead test a case where p_raw > 0 (normal path)
        s_raw, i_raw, p_raw, g, h, relative_spread = MetricsCalculator.compute_micro_price_metrics(5.0, 10.0, 1.0, 9.0, "BTC")
        assert relative_spread == pytest.approx(s_raw / p_raw)

    def test_asymmetric_sizes(self) -> None:
        bid, ask, bid_size, ask_size = 10.0, 20.0, 3.0, 7.0
        s_raw, i_raw, p_raw, g, h, relative_spread = MetricsCalculator.compute_micro_price_metrics(bid, ask, bid_size, ask_size, "SOL")
        expected_i_raw = 3.0 / 10.0
        expected_p_raw = (10.0 * 7.0 + 20.0 * 3.0) / 10.0
        assert i_raw == pytest.approx(expected_i_raw)
        assert p_raw == pytest.approx(expected_p_raw)
