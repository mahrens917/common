"""Tests for result builder."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from unittest.mock import patch

import pytest

from common.market_filters.kalshi_helpers.result_builder import (
    MarketPricingInfo,
    MarketStrikeInfo,
    build_failure_result,
    build_success_result,
)


class TestBuildFailureResult:
    """Tests for build_failure_result function."""

    def test_creates_invalid_result_with_reason(self) -> None:
        """Creates a validation result with is_valid=False."""
        result = build_failure_result(reason="invalid_ticker")

        assert result.is_valid is False
        assert result.reason == "invalid_ticker"

    def test_includes_expiry_when_provided(self) -> None:
        """Includes expiry in result when provided."""
        expiry = datetime(2025, 1, 15, 12, 0, 0)

        result = build_failure_result(
            reason="test_reason",
            expiry=expiry,
        )

        assert result.expiry == expiry

    def test_includes_expiry_raw_when_provided(self) -> None:
        """Includes expiry_raw in result when provided."""
        result = build_failure_result(
            reason="test_reason",
            expiry_raw="2025-01-15",
        )

        assert result.expiry_raw == "2025-01-15"

    def test_includes_strike_when_provided(self) -> None:
        """Includes strike in result when provided."""
        result = build_failure_result(
            reason="test_reason",
            strike=50.0,
        )

        assert result.strike == 50.0

    def test_includes_strike_type_when_provided(self) -> None:
        """Includes strike_type in result when provided."""
        result = build_failure_result(
            reason="test_reason",
            strike_type="above",
        )

        assert result.strike_type == "above"

    def test_includes_floor_cap_strikes_when_provided(self) -> None:
        """Includes floor_strike and cap_strike when provided."""
        result = build_failure_result(
            reason="test_reason",
            floor_strike=40.0,
            cap_strike=60.0,
        )

        assert result.floor_strike == 40.0
        assert result.cap_strike == 60.0

    def test_all_optional_fields_default_to_none(self) -> None:
        """All optional fields default to None."""
        result = build_failure_result(reason="test")

        assert result.expiry is None
        assert result.expiry_raw is None
        assert result.strike is None
        assert result.strike_type is None
        assert result.floor_strike is None
        assert result.cap_strike is None


class TestMarketStrikeInfo:
    """Tests for MarketStrikeInfo dataclass."""

    def test_stores_all_fields(self) -> None:
        """MarketStrikeInfo stores all provided fields."""
        expiry = datetime(2025, 1, 15, 12, 0, 0)

        info = MarketStrikeInfo(
            expiry=expiry,
            expiry_raw="2025-01-15",
            strike=50.0,
            strike_type="above",
            floor_strike=40.0,
            cap_strike=60.0,
        )

        assert info.expiry == expiry
        assert info.expiry_raw == "2025-01-15"
        assert info.strike == 50.0
        assert info.strike_type == "above"
        assert info.floor_strike == 40.0
        assert info.cap_strike == 60.0

    def test_is_frozen(self) -> None:
        """MarketStrikeInfo is frozen (immutable)."""
        info = MarketStrikeInfo(
            expiry=datetime(2025, 1, 15, 12, 0, 0),
            expiry_raw="2025-01-15",
            strike=50.0,
            strike_type="above",
            floor_strike=None,
            cap_strike=None,
        )

        with pytest.raises(FrozenInstanceError):
            info.strike = 60.0  # type: ignore[misc]

    def test_accepts_none_for_floor_cap(self) -> None:
        """MarketStrikeInfo accepts None for floor_strike and cap_strike."""
        info = MarketStrikeInfo(
            expiry=datetime(2025, 1, 15, 12, 0, 0),
            expiry_raw="2025-01-15",
            strike=50.0,
            strike_type="above",
            floor_strike=None,
            cap_strike=None,
        )

        assert info.floor_strike is None
        assert info.cap_strike is None


class TestMarketPricingInfo:
    """Tests for MarketPricingInfo dataclass."""

    def test_stores_all_fields(self) -> None:
        """MarketPricingInfo stores all provided fields."""
        info = MarketPricingInfo(
            bid_price=0.45,
            bid_size=100,
            ask_price=0.55,
            ask_size=50,
            has_orderbook=True,
        )

        assert info.bid_price == 0.45
        assert info.bid_size == 100
        assert info.ask_price == 0.55
        assert info.ask_size == 50
        assert info.has_orderbook is True

    def test_is_frozen(self) -> None:
        """MarketPricingInfo is frozen (immutable)."""
        info = MarketPricingInfo(
            bid_price=0.45,
            bid_size=100,
            ask_price=0.55,
            ask_size=50,
            has_orderbook=True,
        )

        with pytest.raises(FrozenInstanceError):
            info.bid_price = 0.50  # type: ignore[misc]

    def test_accepts_none_for_optional_fields(self) -> None:
        """MarketPricingInfo accepts None for optional price/size fields."""
        info = MarketPricingInfo(
            bid_price=None,
            bid_size=None,
            ask_price=None,
            ask_size=None,
            has_orderbook=False,
        )

        assert info.bid_price is None
        assert info.bid_size is None
        assert info.ask_price is None
        assert info.ask_size is None


class TestBuildSuccessResult:
    """Tests for build_success_result function."""

    def test_creates_valid_result(self) -> None:
        """Creates a validation result with is_valid=True."""
        strike_info = MarketStrikeInfo(
            expiry=datetime(2025, 1, 15, 12, 0, 0),
            expiry_raw="2025-01-15",
            strike=50.0,
            strike_type="above",
            floor_strike=None,
            cap_strike=None,
        )
        pricing_info = MarketPricingInfo(
            bid_price=0.45,
            bid_size=100,
            ask_price=0.55,
            ask_size=50,
            has_orderbook=True,
        )

        with patch(
            "common.market_filters.kalshi_helpers.pricing_validator.check_side_validity"
        ) as mock_check:
            mock_check.return_value = True
            result = build_success_result(strike_info, pricing_info)

        assert result.is_valid is True
        assert result.reason is None

    def test_includes_strike_info(self) -> None:
        """Includes strike info in result."""
        expiry = datetime(2025, 1, 15, 12, 0, 0)
        strike_info = MarketStrikeInfo(
            expiry=expiry,
            expiry_raw="2025-01-15",
            strike=50.0,
            strike_type="above",
            floor_strike=40.0,
            cap_strike=60.0,
        )
        pricing_info = MarketPricingInfo(
            bid_price=0.45,
            bid_size=100,
            ask_price=0.55,
            ask_size=50,
            has_orderbook=True,
        )

        with patch(
            "common.market_filters.kalshi_helpers.pricing_validator.check_side_validity"
        ) as mock_check:
            mock_check.return_value = True
            result = build_success_result(strike_info, pricing_info)

        assert result.expiry == expiry
        assert result.expiry_raw == "2025-01-15"
        assert result.strike == 50.0
        assert result.strike_type == "above"
        assert result.floor_strike == 40.0
        assert result.cap_strike == 60.0

    def test_includes_pricing_when_valid(self) -> None:
        """Includes pricing info when sides are valid."""
        strike_info = MarketStrikeInfo(
            expiry=datetime(2025, 1, 15, 12, 0, 0),
            expiry_raw="2025-01-15",
            strike=50.0,
            strike_type="above",
            floor_strike=None,
            cap_strike=None,
        )
        pricing_info = MarketPricingInfo(
            bid_price=0.45,
            bid_size=100,
            ask_price=0.55,
            ask_size=50,
            has_orderbook=True,
        )

        with patch(
            "common.market_filters.kalshi_helpers.pricing_validator.check_side_validity"
        ) as mock_check:
            mock_check.return_value = True
            result = build_success_result(strike_info, pricing_info)

        assert result.yes_bid_price == 0.45
        assert result.yes_bid_size == 100
        assert result.yes_ask_price == 0.55
        assert result.yes_ask_size == 50
        assert result.has_orderbook is True

    def test_excludes_pricing_when_invalid(self) -> None:
        """Excludes pricing info when sides are invalid."""
        strike_info = MarketStrikeInfo(
            expiry=datetime(2025, 1, 15, 12, 0, 0),
            expiry_raw="2025-01-15",
            strike=50.0,
            strike_type="above",
            floor_strike=None,
            cap_strike=None,
        )
        pricing_info = MarketPricingInfo(
            bid_price=None,
            bid_size=None,
            ask_price=None,
            ask_size=None,
            has_orderbook=False,
        )

        with patch(
            "common.market_filters.kalshi_helpers.pricing_validator.check_side_validity"
        ) as mock_check:
            mock_check.return_value = False
            result = build_success_result(strike_info, pricing_info)

        assert result.yes_bid_price is None
        assert result.yes_bid_size is None
        assert result.yes_ask_price is None
        assert result.yes_ask_size is None

    def test_last_price_is_none(self) -> None:
        """Last price is always None in result."""
        strike_info = MarketStrikeInfo(
            expiry=datetime(2025, 1, 15, 12, 0, 0),
            expiry_raw="2025-01-15",
            strike=50.0,
            strike_type="above",
            floor_strike=None,
            cap_strike=None,
        )
        pricing_info = MarketPricingInfo(
            bid_price=0.45,
            bid_size=100,
            ask_price=0.55,
            ask_size=50,
            has_orderbook=True,
        )

        with patch(
            "common.market_filters.kalshi_helpers.pricing_validator.check_side_validity"
        ) as mock_check:
            mock_check.return_value = True
            result = build_success_result(strike_info, pricing_info)

        assert result.last_price is None
