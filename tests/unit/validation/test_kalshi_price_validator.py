"""Tests for Kalshi price validation utilities."""

import pytest

from common.validation.kalshi_price_validator import (
    KALSHI_MAX_PRICE_CENTS,
    KALSHI_MIN_PRICE_CENTS,
    validate_kalshi_bid_ask_relationship,
    validate_kalshi_price_bounds,
    validate_kalshi_price_pair,
)


def test_validate_bid_ask_relationship_allows_equal():
    validate_kalshi_bid_ask_relationship(10, 10)


def test_validate_bid_ask_relationship_rejects_invalid():
    with pytest.raises(RuntimeError):
        validate_kalshi_bid_ask_relationship(11, 10)


def test_validate_price_bounds_accepts_values():
    validate_kalshi_price_bounds(KALSHI_MIN_PRICE_CENTS, "price")
    validate_kalshi_price_bounds(KALSHI_MAX_PRICE_CENTS, "price")


def test_validate_price_bounds_rejects_negative():
    with pytest.raises(TypeError):
        validate_kalshi_price_bounds(-1, "price")


def test_validate_price_bounds_rejects_too_high():
    with pytest.raises(ValueError):
        validate_kalshi_price_bounds(KALSHI_MAX_PRICE_CENTS + 1, "price")


def test_validate_price_pair_handles_optional_values():
    validate_kalshi_price_pair(None, 10)
    validate_kalshi_price_pair(10, None)


def test_validate_price_pair_flags_errors():
    with pytest.raises(RuntimeError):
        validate_kalshi_price_pair(20, 10)
