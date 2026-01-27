"""Tests for market_ownership module."""

import pytest

from common.redis_protocol.market_ownership import can_algo_own_market, get_required_owner


class TestGetRequiredOwner:
    """Tests for get_required_owner function."""

    def test_weather_high_returns_weather(self):
        """KXHIGH markets require weather algo."""
        result = get_required_owner("KXHIGHNY-25DEC28-T44")
        assert result == "weather"

    def test_weather_low_returns_weather(self):
        """KXLOW markets require weather algo."""
        result = get_required_owner("KXLOWCHI-25DEC28-T30")
        assert result == "weather"

    def test_weather_case_insensitive(self):
        """Ticker matching is case-insensitive."""
        result = get_required_owner("kxhighny-25dec28-t44")
        assert result == "weather"

    def test_weather_with_mutually_exclusive_false_returns_none(self):
        """Non-ME weather markets can be owned by any algo."""
        result = get_required_owner("KXHIGHNY-25DEC28-T44", {"mutually_exclusive": False})
        assert result is None

    def test_weather_with_mutually_exclusive_true_returns_weather(self):
        """ME weather markets require weather algo."""
        result = get_required_owner("KXHIGHNY-25DEC28-T44", {"mutually_exclusive": True})
        assert result == "weather"

    def test_weather_with_mutually_exclusive_string_true(self):
        """String 'true' is accepted for mutually_exclusive."""
        result = get_required_owner("KXHIGHNY-25DEC28-T44", {"mutually_exclusive": "true"})
        assert result == "weather"

    def test_pdf_btc_returns_pdf(self):
        """KXBTC markets require pdf algo."""
        result = get_required_owner("KXBTCD-25JAN28-T100000")
        assert result == "pdf"

    def test_pdf_eth_returns_pdf(self):
        """KXETH markets require pdf algo."""
        result = get_required_owner("KXETHD-25JAN28-T4000")
        assert result == "pdf"

    def test_pdf_with_mutually_exclusive_false_returns_none(self):
        """Non-ME PDF markets can be owned by any algo."""
        result = get_required_owner("KXBTCD-25JAN28-T100000", {"mutually_exclusive": False})
        assert result is None

    def test_other_market_returns_none(self):
        """Other markets have no required owner."""
        result = get_required_owner("INXD-25JAN28-T20000")
        assert result is None

    def test_empty_market_data_assumes_me(self):
        """Empty market data assumes mutually_exclusive=True."""
        result = get_required_owner("KXHIGHNY-25DEC28-T44", {})
        assert result == "weather"


class TestCanAlgoOwnMarket:
    """Tests for can_algo_own_market function."""

    def test_weather_can_own_weather_market(self):
        """Weather algo can own weather market."""
        result = can_algo_own_market("weather", "KXHIGHNY-25DEC28-T44")
        assert result is True

    def test_peak_cannot_own_weather_market(self):
        """Peak algo cannot own weather market."""
        result = can_algo_own_market("peak", "KXHIGHNY-25DEC28-T44")
        assert result is False

    def test_pdf_can_own_pdf_market(self):
        """PDF algo can own PDF market."""
        result = can_algo_own_market("pdf", "KXBTCD-25JAN28-T100000")
        assert result is True

    def test_weather_cannot_own_pdf_market(self):
        """Weather algo cannot own PDF market."""
        result = can_algo_own_market("weather", "KXBTCD-25JAN28-T100000")
        assert result is False

    def test_any_algo_can_own_generic_market(self):
        """Any algo can own generic markets."""
        assert can_algo_own_market("peak", "INXD-25JAN28-T20000") is True
        assert can_algo_own_market("weather", "INXD-25JAN28-T20000") is True
        assert can_algo_own_market("pdf", "INXD-25JAN28-T20000") is True

    def test_first_algo_wins_speed_rule(self):
        """First algo to claim wins (speed rule)."""
        result = can_algo_own_market("peak", "INXD-25JAN28-T20000", current_owner="edge")
        assert result is False

    def test_same_algo_can_update(self):
        """Same algo can update its own market."""
        result = can_algo_own_market("peak", "INXD-25JAN28-T20000", current_owner="peak")
        assert result is True

    def test_no_owner_allows_claim(self):
        """Market with no owner can be claimed."""
        result = can_algo_own_market("peak", "INXD-25JAN28-T20000", current_owner=None)
        assert result is True

    def test_non_me_weather_market_any_algo(self):
        """Non-ME weather market can be owned by any algo."""
        market_data = {"mutually_exclusive": False}
        result = can_algo_own_market("peak", "KXHIGHNY-25DEC28-T44", market_data=market_data)
        assert result is True

    def test_required_owner_takes_precedence_over_speed(self):
        """Required owner constraint takes precedence even with no current owner."""
        result = can_algo_own_market("peak", "KXHIGHNY-25DEC28-T44", current_owner=None)
        assert result is False
